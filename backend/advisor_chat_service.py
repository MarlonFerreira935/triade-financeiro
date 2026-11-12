"""Conversation lifecycle and streaming, independent of HTTP route declarations."""
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from advisor_service import consult, live_snapshot


def sse(payload):
    return 'data: ' + json.dumps(payload) + '\n\n'


@dataclass
class ChatRequest:
    conversation_id: str
    request_id: str
    user_message: dict
    snapshot: dict
    history: list
    text: str


class AdvisorChatService:
    def __init__(self, db):
        self.db = db

    async def find_conversation(self, conversation_id):
        record = await self.db.conversations.find_one({'id': conversation_id, 'is_deleted': {'$ne': True}}, {'_id': 0, 'busy_until': 0, 'request_id': 0})
        if not record:
            raise HTTPException(404, 'Conversa não encontrada.')
        return record

    async def open_conversation(self, data, now):
        if data.conversation_id:
            record = await self.find_conversation(data.conversation_id)
            if record['month'] != data.month:
                raise HTTPException(409, 'O período da conversa é diferente. Inicie uma nova conversa.')
            return record['id']
        conversation_id = str(uuid.uuid4())
        record = {'id': conversation_id, 'month': data.month, 'title': data.message[:80], 'channel': 'web', 'is_deleted': False,
                  'created_at': now.isoformat(), 'updated_at': now.isoformat()}
        await self.db.conversations.insert_one(record.copy())
        return conversation_id

    async def acquire(self, conversation_id, request_id, now):
        query = {'id': conversation_id, 'is_deleted': {'$ne': True}, '$or': [{'busy_until': {'$exists': False}}, {'busy_until': {'$lte': now.isoformat()}}]}
        result = await self.db.conversations.update_one(query, {'$set': {
            'busy_until': (now + timedelta(seconds=150)).isoformat(), 'request_id': request_id, 'updated_at': now.isoformat()}})
        if not result.modified_count:
            raise HTTPException(409, 'Aguarde a resposta atual antes de enviar outra pergunta.')

    async def release(self, conversation_id, request_id):
        await self.db.conversations.update_one({'id': conversation_id, 'request_id': request_id}, {
            '$unset': {'busy_until': '', 'request_id': ''}, '$set': {'updated_at': datetime.now(timezone.utc).isoformat()}})

    async def user_message(self, conversation_id, data, now):
        if data.retry_message_id:
            message = await self.db.advisor_messages.find_one({'id': data.retry_message_id,
                'conversation_id': conversation_id, 'role': 'user', 'content': data.message}, {'_id': 0})
            if not message:
                raise HTTPException(400, 'A pergunta original não foi encontrada para tentar novamente.')
            completed = await self.db.advisor_messages.find_one({'conversation_id': conversation_id,
                'reply_to': message['id'], 'status': 'complete'}, {'_id': 0, 'id': 1})
            if completed:
                raise HTTPException(409, 'Esta pergunta já foi respondida. Abra novamente a conversa no histórico.')
            return message
        message = {'id': str(uuid.uuid4()), 'conversation_id': conversation_id, 'role': 'user',
                   'content': data.message, 'status': 'complete', 'created_at': now.isoformat()}
        await self.db.advisor_messages.insert_one(message.copy())
        return message

    async def prepare(self, data):
        now = datetime.now(timezone.utc)
        if await self.db.conversations.count_documents({'busy_until': {'$gt': now.isoformat()}}) >= 4:
            raise HTTPException(429, 'Há análises em andamento. Aguarde alguns instantes.')
        conversation_id = await self.open_conversation(data, now)
        request_id = str(uuid.uuid4())
        await self.acquire(conversation_id, request_id, now)
        try:
            snapshot = await live_snapshot(self.db, data.month)
            history_query = {'conversation_id': conversation_id, 'status': 'complete'}
            if data.retry_message_id:
                history_query['id'] = {'$ne': data.retry_message_id}
            history = await self.db.advisor_messages.find(history_query, {'_id': 0, 'role': 1, 'content': 1}).sort('created_at', -1).limit(16).to_list(16)
            user_message = await self.user_message(conversation_id, data, now)
            return ChatRequest(conversation_id, request_id, user_message, snapshot, list(reversed(history)), data.message)
        except BaseException:
            await asyncio.shield(self.release(conversation_id, request_id))
            raise

    async def persist_result(self, request, assistant_id, answer, status):
        try:
            await self.db.advisor_messages.insert_one({'id': assistant_id, 'conversation_id': request.conversation_id,
                'role': 'assistant', 'content': answer, 'status': status, 'reply_to': request.user_message['id'],
                'created_at': datetime.now(timezone.utc).isoformat(), 'data_as_of': request.snapshot['updated_at'],
                'month': request.snapshot['month'], 'record_count': request.snapshot['totals']['count']})
        finally:
            await self.release(request.conversation_id, request.request_id)

    async def events(self, request):
        answer, status, assistant_id = '', 'failed', str(uuid.uuid4())
        # The first yield belongs inside try/finally so a disconnect after metadata also releases the lock.
        try:
            yield sse({'type': 'meta', 'conversation_id': request.conversation_id,
                'user_message_id': request.user_message['id'], 'assistant_id': assistant_id,
                'month': request.snapshot['month'], 'updated_at': request.snapshot['updated_at'],
                'record_count': request.snapshot['totals']['count']})
            async with asyncio.timeout(120):
                async for chunk in consult(request.snapshot, request.history, request.text):
                    answer += chunk
                    yield sse({'type': 'delta', 'text': chunk})
            if not answer.strip():
                raise RuntimeError('Resposta vazia')
            status = 'complete'
        except asyncio.CancelledError:
            status = 'interrupted'
            raise
        except Exception:
            logging.exception('Falha no consultor financeiro')
            yield sse({'type': 'error', 'message': 'A análise não foi concluída. Sua pergunta foi salva; você pode tentar novamente.'})
        finally:
            await asyncio.shield(self.persist_result(request, assistant_id, answer, status))
        if status == 'complete':
            yield sse({'type': 'done', 'conversation_id': request.conversation_id, 'assistant_id': assistant_id})