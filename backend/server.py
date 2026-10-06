import os
import re
import io
import json
import uuid
import asyncio
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response, StreamingResponse, FileResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from PIL import Image, UnidentifiedImageError
from finance import ACCOUNTS, ACCOUNT_MAP, ROW_LABELS, MONTHS, TEMPLATE, parse_workbook, totals, diagnostics, export_workbook
from storage_service import init_storage, put_object, get_object
from ai_service import extract_receipt, stream_diagnostics

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
logger = logging.getLogger(__name__)
MONTH_PATTERN = r'^\d{4}-(0[1-9]|1[0-2])$'

@asynccontextmanager
async def lifespan(app):
    await db.transactions.create_index('id',unique=True)
    await db.receipts.create_index('id',unique=True)
    await db.conversations.create_index('id',unique=True)
    await db.advisor_messages.create_index([('conversation_id',1),('created_at',1)])
    await db.alert_acknowledgements.create_index('id',unique=True)
    if not await db.settings.find_one({'id':'initial_import'}):
        records = parse_workbook(TEMPLATE.read_bytes(),2026)
        for record in records:
            await db.transactions.update_one({'id':record['id']},{'$setOnInsert':record},upsert=True)
        await db.settings.update_one({'id':'initial_import'},{'$set':{'done':True}},upsert=True)
        await db.imports.insert_one({'id':str(uuid.uuid4()),'filename':'TRIADE_ERP_FINANCEIRO FINAL PADRÃO (2).xlsx','year':2026,'count':len(records),'created_at':datetime.now(timezone.utc).isoformat()})
    try: await run_in_threadpool(init_storage)
    except Exception: logger.exception('Armazenamento indisponível na inicialização')
    yield
    client.close()

app=FastAPI(title='Tríade Financeiro',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.environ['CORS_ORIGINS'].split(','),allow_credentials=False,allow_methods=['*'],allow_headers=['*'])
api=APIRouter(prefix='/api')

class TransactionInput(BaseModel):
    description: str = Field(min_length=2,max_length=250)
    amount: float = Field(gt=0,le=100000000,allow_inf_nan=False)
    date: date
    account_id: str
    type: Literal['receita','despesa']
    receipt_id: Optional[str] = None
    note: str = Field(default='',max_length=2000)
    @field_validator('account_id')
    @classmethod
    def valid_account(cls,value):
        if value not in ACCOUNT_MAP: raise ValueError('Conta inválida')
        return value

class Transaction(TransactionInput):
    id: str
    category: str
    source: str
    status: str = 'confirmado'
    created_at: str

async def records_for(month=None,year=None):
    q={}
    if month:q['date']={'$regex':'^'+re.escape(month)}
    elif year:q['date']={'$regex':f'^{year}-'}
    return await db.transactions.find(q,{'_id':0}).sort('date',-1).to_list(50000)

@api.get('/')
async def health():return {'status':'ok','app':'Tríade Financeiro'}

@api.get('/meta')
async def meta():
    dates=await db.transactions.distinct('date')
    months=sorted({d[:7] for d in dates},reverse=True)
    return {'accounts':ACCOUNTS,'months':months,'default_month':months[0] if months else date.today().strftime('%Y-%m'),'whatsapp_connected':False}

@api.get('/dashboard')
async def dashboard(month: str=Query(pattern=MONTH_PATTERN)):
    records=await records_for(month=month)
    t=totals(records)
    y,m=map(int,month.split('-'))
    prev=f'{y if m>1 else y-1}-{m-1 if m>1 else 12:02}'
    previous=totals(await records_for(month=prev))
    annual=await records_for(year=y)
    chart=[]
    for n in range(1,13):
        month_records=[r for r in annual if r['date'].startswith(f'{y}-{n:02}')]
        values=totals(month_records)
        chart.append({'name':MONTHS[n-1],'receitas':values['revenue'] if month_records else None,'despesas':values['expenses'] if month_records else None,'lucro':values['profit'] if month_records else None})
    categories={}
    for r in records:
        if r['type']=='despesa' and int(r['account_id'])<70:categories[r['category']]=round(categories.get(r['category'],0)+r['amount'],2)
    expenses=sorted([{'name':k,'value':v} for k,v in categories.items()],key=lambda c:c['value'],reverse=True)
    receipt_count=await db.receipts.count_documents({'date':{'$regex':'^'+month},'is_deleted':False})
    pending=await db.receipts.count_documents({'is_deleted':False,'status':'pendente'})
    return {'month':month,'totals':t,'previous':previous,'chart':chart,'categories':expenses,'recent':records[:6],
        'diagnostics':diagnostics(t),'receipt_count':receipt_count,'pending_receipts':pending}

@api.get('/transactions',response_model=list[Transaction])
async def transactions(month:Optional[str]=Query(default=None,pattern=MONTH_PATTERN),search:str='',kind:str='todos',category:str='todas'):
    records=await records_for(month=month)
    return [r for r in records if (not search or search.casefold() in (r['description']+' '+r['category']).casefold()) and (kind=='todos' or r['type']==kind) and (category=='todas' or r['category']==category)]

async def validated_record(data,existing=None):
    account=ACCOUNT_MAP[data.account_id]
    if data.type != account['type']:raise HTTPException(422,'O tipo deve corresponder à conta selecionada.')
    if data.receipt_id:
        receipt=await db.receipts.find_one({'id':data.receipt_id,'is_deleted':False},{'_id':0})
        if not receipt:raise HTTPException(404,'Comprovante não encontrado.')
        if receipt.get('transaction_id') and receipt['transaction_id'] != (existing or {}).get('id'):
            raise HTTPException(409,'Este comprovante já tem um lançamento.')
    return {**data.model_dump(mode='json'),'amount':round(data.amount,2),'category':account['group']}

async def link_receipt(record):
    if record.get('receipt_id'):
        await db.receipts.update_one({'id':record['receipt_id']},{'$set':{'status':'lancado','transaction_id':record['id'],'date':record['date'],'category':record['category'],'amount':record['amount']}})

@api.post('/transactions',response_model=Transaction,status_code=201)
async def create_transaction(data:TransactionInput):
    record={**await validated_record(data),'id':str(uuid.uuid4()),'status':'confirmado','source':'comprovante' if data.receipt_id else 'manual','created_at':datetime.now(timezone.utc).isoformat()}
    await db.transactions.insert_one(record.copy());await link_receipt(record)
    return Transaction(**record)

@api.put('/transactions/{transaction_id}',response_model=Transaction)
async def update_transaction(transaction_id:str,data:TransactionInput):
    existing=await db.transactions.find_one({'id':transaction_id},{'_id':0})
    if not existing:raise HTTPException(404,'Lançamento não encontrado.')
    record={**existing,**await validated_record(data,existing)}
    if existing.get('receipt_id') and existing['receipt_id']!=record.get('receipt_id'):
        await db.receipts.update_one({'id':existing['receipt_id']},{'$set':{'status':'pendente','transaction_id':None}})
    await db.transactions.update_one({'id':transaction_id},{'$set':record});await link_receipt(record)
    return Transaction(**record)

@api.delete('/transactions/{transaction_id}')
async def delete_transaction(transaction_id:str):
    result=await db.transactions.delete_one({'id':transaction_id})
    if not result.deleted_count:raise HTTPException(404,'Lançamento não encontrado.')
    await db.receipts.update_many({'transaction_id':transaction_id},{'$set':{'status':'pendente','transaction_id':None}})
    return {'deleted':True}

@api.get('/dre')
async def dre(year:int=Query(ge=2000,le=2100)):
    records=await records_for(year=year)
    monthly=[totals([r for r in records if r['date'].startswith(f'{year}-{m:02}')]) for m in range(1,13)]
    calculated={11:'net_revenue',32:'contribution',33:'contribution_margin',58:'ebitda',63:'ebit',67:'profit',68:'margin',73:'free_cash'}
    rows=[]
    for r,label in ROW_LABELS.items():
        is_account=str(r) in ACCOUNT_MAP
        values=[t['accounts'][str(r)] if is_account else t.get(calculated.get(r,''),0) for t in monthly]
        if r==59:values=[round(t['ebitda']/t['net_revenue']*100,2) if t['net_revenue'] else 0 for t in monthly]
        rows.append({'row':r,'label':label,'values':values,'account':is_account,'subtotal':r in calculated or r==59,'percentage':r in [33,59,68]})
    return {'year':year,'rows':rows,'months':MONTHS,'totals':totals(records)}

@api.get('/spreadsheet/original')
async def original():return FileResponse(TEMPLATE,filename='TRIADE_ERP_FINANCEIRO_ORIGINAL.xlsx')

@api.get('/spreadsheet/export')
async def export(year:int=Query(ge=2000,le=2100)):
    content=await run_in_threadpool(export_workbook,await records_for(year=year),year)
    return Response(content,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':f'attachment; filename="TRIADE_FINANCEIRO_{year}.xlsx"'})

@api.post('/spreadsheet/import')
async def import_sheet(file:UploadFile=File(...),year:int=Form(2026)):
    if not 2000<=year<=2100:raise HTTPException(422,'Ano inválido.')
    if not file.filename.lower().endswith('.xlsx'):raise HTTPException(400,'Envie uma planilha .xlsx no modelo Tríade.')
    content=await file.read(10*1024*1024+1)
    if len(content)>10*1024*1024:raise HTTPException(413,'Limite de 10 MB.')
    try:
        import openpyxl
        workbook=openpyxl.load_workbook(io.BytesIO(content),read_only=True)
        if 'Lançamentos do Sistema' in workbook.sheetnames:
            raise ValueError('Esta planilha foi exportada pelo sistema e já contém os lançamentos atuais. Reimportação bloqueada para evitar duplicidade.')
        workbook.close()
        records=await run_in_threadpool(parse_workbook,content,year)
    except Exception as exc:raise HTTPException(400,str(exc) if isinstance(exc,ValueError) else 'Arquivo Excel inválido ou corrompido.')
    if not records:raise HTTPException(400,'Nenhum valor encontrado. A base atual foi mantida.')
    for record in records:await db.transactions.update_one({'id':record['id']},{'$set':record},upsert=True)
    await db.transactions.delete_many({'source':'planilha','date':{'$regex':f'^{year}-'},'id':{'$nin':[r['id'] for r in records]}})
    result={'id':str(uuid.uuid4()),'filename':file.filename,'year':year,'count':len(records),'created_at':datetime.now(timezone.utc).isoformat()}
    await db.imports.insert_one(result.copy())
    return result

@api.get('/spreadsheet/history')
async def history():return await db.imports.find({},{'_id':0}).sort('created_at',-1).to_list(100)

@api.get('/diagnostics/latest')
async def latest_diagnostic(month:str=Query(pattern=MONTH_PATTERN)):
    return await db.diagnostics.find_one({'month':month},{'_id':0},sort=[('created_at',-1)]) or {'text':''}

@api.get('/diagnostics/stream')
async def diagnostic_stream(month:str=Query(pattern=MONTH_PATTERN)):
    summary=totals(await records_for(month=month))
    if not summary['count']:raise HTTPException(400,'Sem dados para analisar neste período.')
    async def events():
        text=''
        try:
            async for chunk in stream_diagnostics({'month':month,**summary}):
                text+=chunk;yield 'data: '+json.dumps({'text':chunk})+'\n\n'
            await db.diagnostics.insert_one({'id':str(uuid.uuid4()),'month':month,'text':text,'created_at':datetime.now(timezone.utc).isoformat()})
            yield 'data: '+json.dumps({'done':True})+'\n\n'
        except Exception:
            logger.exception('Falha no diagnóstico');yield 'data: '+json.dumps({'error':'Não foi possível concluir a análise. Tente novamente.'})+'\n\n'
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

from receipt_routes import create_receipt_router
app.include_router(api)
app.include_router(create_receipt_router(db))
from advisor_routes import create_advisor_router
app.include_router(create_advisor_router(db))