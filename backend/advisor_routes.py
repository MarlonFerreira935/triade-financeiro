import asyncio
import uuid
import json
import logging
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,HTTPException,Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field,field_validator
from advisor_service import live_snapshot,alert_feed,consult

MONTH_PATTERN=r'^\d{4}-(0[1-9]|1[0-2])$'

class ConsultInput(BaseModel):
    message:str=Field(min_length=1,max_length=4000)
    month:str=Field(pattern=MONTH_PATTERN)
    conversation_id:str|None=Field(default=None,max_length=80)
    @field_validator('message')
    @classmethod
    def not_blank(cls,value):
        if not value.strip():raise ValueError('Digite sua pergunta.')
        return value.strip()

class AcknowledgeInput(BaseModel):
    month:str=Field(pattern=MONTH_PATTERN)
    acknowledged:bool=True

def create_advisor_router(db):
    router=APIRouter(prefix='/api')

    @router.get('/alerts')
    async def alerts(month:str=Query(pattern=MONTH_PATTERN)):
        return await alert_feed(db,month)

    @router.put('/alerts/{alert_id}/acknowledge')
    async def acknowledge(alert_id:str,data:AcknowledgeInput):
        feed=await alert_feed(db,data.month)
        alert=next((a for a in feed['alerts'] if a['id']==alert_id),None)
        if not alert:raise HTTPException(404,'Este alerta não está mais ativo.')
        if data.acknowledged:
            await db.alert_acknowledgements.update_one({'id':alert_id},{'$set':{'id':alert_id,'month':data.month,'metric':alert['metric'],'acknowledged_at':datetime.now(timezone.utc).isoformat()}},upsert=True)
        else:await db.alert_acknowledgements.delete_one({'id':alert_id})
        return {'id':alert_id,'acknowledged':data.acknowledged}

    @router.get('/advisor/conversations')
    async def conversations(month:str=Query(pattern=MONTH_PATTERN)):
        return await db.conversations.find({'month':month},{'_id':0,'busy_until':0,'request_id':0}).sort('updated_at',-1).to_list(100)

    @router.get('/advisor/conversations/{cid}')
    async def conversation(cid:str):
        record=await db.conversations.find_one({'id':cid},{'_id':0,'busy_until':0,'request_id':0})
        if not record:raise HTTPException(404,'Conversa não encontrada.')
        messages=await db.advisor_messages.find({'conversation_id':cid},{'_id':0}).sort('created_at',1).to_list(500)
        return {**record,'messages':messages}

    @router.delete('/advisor/conversations/{cid}')
    async def delete_conversation(cid:str):
        now=datetime.now(timezone.utc).isoformat()
        record=await db.conversations.find_one({'id':cid},{'_id':0})
        if not record:raise HTTPException(404,'Conversa não encontrada.')
        if record.get('busy_until','')>now:raise HTTPException(409,'Aguarde a resposta antes de excluir a conversa.')
        await db.conversations.delete_one({'id':cid});await db.advisor_messages.delete_many({'conversation_id':cid})
        return {'deleted':True}

    @router.post('/advisor/chat')
    async def chat_message(data:ConsultInput):
        now=datetime.now(timezone.utc)
        if await db.conversations.count_documents({'busy_until':{'$gt':now.isoformat()}})>=4:
            raise HTTPException(429,'Há análises em andamento. Aguarde alguns instantes.')
        cid=data.conversation_id or str(uuid.uuid4())
        if data.conversation_id:
            record=await db.conversations.find_one({'id':cid},{'_id':0})
            if not record:raise HTTPException(404,'Conversa não encontrada.')
            if record['month']!=data.month:raise HTTPException(409,'O período da conversa é diferente. Inicie uma nova conversa.')
        else:
            record={'id':cid,'month':data.month,'title':data.message[:80],'channel':'web','created_at':now.isoformat(),'updated_at':now.isoformat()}
            await db.conversations.insert_one(record.copy())
        request_id=str(uuid.uuid4())
        locked=await db.conversations.update_one({'id':cid,'$or':[{'busy_until':{'$exists':False}},{'busy_until':{'$lte':now.isoformat()}}]},
            {'$set':{'busy_until':(now+timedelta(seconds=150)).isoformat(),'request_id':request_id,'updated_at':now.isoformat()}})
        if not locked.modified_count:raise HTTPException(409,'Aguarde a resposta atual antes de enviar outra pergunta.')
        try:
            snapshot=await live_snapshot(db,data.month)
            history=await db.advisor_messages.find({'conversation_id':cid,'status':'complete'},{'_id':0,'role':1,'content':1}).sort('created_at',-1).limit(16).to_list(16)
            history.reverse()
            user_message={'id':str(uuid.uuid4()),'conversation_id':cid,'role':'user','content':data.message,'status':'complete','created_at':now.isoformat()}
            await db.advisor_messages.insert_one(user_message.copy())
        except Exception:
            await db.conversations.update_one({'id':cid,'request_id':request_id},{'$unset':{'busy_until':'','request_id':''}})
            raise

        async def events():
            answer='';status='failed'
            assistant_id=str(uuid.uuid4())
            yield 'data: '+json.dumps({'type':'meta','conversation_id':cid,'user_message_id':user_message['id'],'assistant_id':assistant_id,
                'month':data.month,'updated_at':snapshot['updated_at'],'record_count':snapshot['totals']['count']})+'\n\n'
            try:
                async with asyncio.timeout(120):
                    async for chunk in consult(snapshot,history,data.message):
                        answer+=chunk
                        yield 'data: '+json.dumps({'type':'delta','text':chunk})+'\n\n'
                if not answer.strip():raise RuntimeError('Resposta vazia')
                status='complete'
            except asyncio.CancelledError:
                status='interrupted';raise
            except Exception:
                logging.exception('Falha no consultor financeiro')
                yield 'data: '+json.dumps({'type':'error','message':'A análise não foi concluída. Sua pergunta foi salva; você pode tentar novamente.'})+'\n\n'
            finally:
                async def persist_result():
                    try:
                        await db.advisor_messages.insert_one({'id':assistant_id,'conversation_id':cid,'role':'assistant','content':answer,'status':status,
                            'created_at':datetime.now(timezone.utc).isoformat(),'data_as_of':snapshot['updated_at'],'month':data.month,'record_count':snapshot['totals']['count']})
                    finally:
                        await db.conversations.update_one({'id':cid,'request_id':request_id},{'$unset':{'busy_until':'','request_id':''},'$set':{'updated_at':datetime.now(timezone.utc).isoformat()}})
                await asyncio.shield(persist_result())
            if status=='complete':yield 'data: '+json.dumps({'type':'done','conversation_id':cid,'assistant_id':assistant_id})+'\n\n'
        return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
    return router