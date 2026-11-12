from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from advisor_chat_service import AdvisorChatService
from advisor_service import alert_feed

MONTH_PATTERN = r'^\d{4}-(0[1-9]|1[0-2])$'


class ConsultInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    month: str = Field(pattern=MONTH_PATTERN)
    conversation_id: str | None = Field(default=None, max_length=80)
    retry_message_id: str | None = Field(default=None, max_length=80)

    @field_validator('message')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Digite sua pergunta.')
        return value.strip()


class AcknowledgeInput(BaseModel):
    month: str = Field(pattern=MONTH_PATTERN)
    acknowledged: bool = True


async def acknowledge_alert(db, alert_id, data):
    feed = await alert_feed(db, data.month)
    alert = next((item for item in feed['alerts'] if item['id'] == alert_id), None)
    if not alert:
        raise HTTPException(404, 'Este alerta não está mais ativo.')
    if data.acknowledged:
        await db.alert_acknowledgements.update_one({'id': alert_id}, {'$set': {
            'id': alert_id, 'month': data.month, 'metric': alert['metric'],
            'acknowledged_at': datetime.now(timezone.utc).isoformat()}}, upsert=True)
    else:
        await db.alert_acknowledgements.delete_one({'id': alert_id})
    return {'id': alert_id, 'acknowledged': data.acknowledged}


def create_advisor_router(db):
    router = APIRouter(prefix='/api')
    service = AdvisorChatService(db)

    @router.get('/alerts')
    async def alerts(month: str = Query(pattern=MONTH_PATTERN)):
        return await alert_feed(db, month)

    @router.put('/alerts/{alert_id}/acknowledge')
    async def acknowledge(alert_id: str, data: AcknowledgeInput):
        return await acknowledge_alert(db, alert_id, data)

    @router.get('/advisor/conversations')
    async def conversations(month: str = Query(pattern=MONTH_PATTERN)):
        return await db.conversations.find({'month': month, 'is_deleted': {'$ne': True}}, {'_id': 0, 'busy_until': 0, 'request_id': 0}).sort('updated_at', -1).to_list(100)

    @router.get('/advisor/conversations/{cid}')
    async def conversation(cid: str):
        record = await service.find_conversation(cid)
        messages = await db.advisor_messages.find({'conversation_id': cid}, {'_id': 0}).sort('created_at', 1).to_list(500)
        return {**record, 'messages': messages}

    @router.delete('/advisor/conversations/{cid}')
    async def delete_conversation(cid: str):
        await service.find_conversation(cid)
        now = datetime.now(timezone.utc).isoformat()
        result = await db.conversations.update_one({'id': cid, 'is_deleted': {'$ne': True}, '$or': [
            {'busy_until': {'$exists': False}}, {'busy_until': {'$lte': now}}]},
            {'$set': {'is_deleted': True, 'deleted_at': now}})
        if not result.modified_count:
            raise HTTPException(409, 'Aguarde a resposta antes de excluir a conversa.')
        return {'deleted': True}

    @router.post('/advisor/chat')
    async def chat_message(data: ConsultInput):
        request = await service.prepare(data)
        return StreamingResponse(service.events(request), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    return router