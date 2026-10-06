import io
import uuid
import asyncio
import logging
from datetime import date,datetime,timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from PIL import Image
from finance import ACCOUNT_MAP
from storage_service import put_object,get_object
from ai_service import extract_receipt

def create_receipt_router(db):
    router=APIRouter(prefix='/api/receipts')

    @router.get('')
    async def list_receipts(month:str='',category:str='todas'):
        query={'is_deleted':False}
        if month:query['date']={'$regex':'^'+__import__('re').escape(month)}
        if category!='todas':query['category']=category
        return await db.receipts.find(query,{'_id':0,'storage_path':0}).sort('created_at',-1).to_list(1000)

    @router.post('',status_code=201)
    async def upload(file:UploadFile=File(...),month:str=Form('')):
        data=await file.read(10*1024*1024+1)
        if len(data)>10*1024*1024:raise HTTPException(413,'O arquivo deve ter até 10 MB.')
        ext=file.filename.rsplit('.',1)[-1].lower()
        mime={'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','webp':'image/webp','pdf':'application/pdf'}.get(ext)
        if not mime:raise HTTPException(400,'Envie JPG, PNG, WEBP ou PDF.')
        if ext=='pdf':
            if not data.startswith(b'%PDF'):raise HTTPException(400,'PDF inválido.')
        else:
            try:
                image=Image.open(io.BytesIO(data));image.verify()
                image=Image.open(io.BytesIO(data));image.seek(0);image.thumbnail((1800,1800));image=image.convert('RGB')
                out=io.BytesIO();image.save(out,format='JPEG',quality=90);ai_data=out.getvalue()
            except Exception:raise HTTPException(400,'Imagem inválida.')
        rid=str(uuid.uuid4())
        path=f'triade-poa/receipts/{datetime.now(timezone.utc):%Y-%m}/{rid}.{ext}'
        try:stored=await run_in_threadpool(put_object,path,data,mime)
        except Exception:
            logging.exception('Falha ao guardar comprovante');raise HTTPException(503,'Não foi possível armazenar o arquivo. Tente novamente.')
        extracted={};error=None
        if ext!='pdf':
            try:extracted=await asyncio.wait_for(extract_receipt(ai_data),timeout=75)
            except Exception:
                logging.exception('Falha na leitura de comprovante');error='Arquivo salvo. A leitura automática não foi concluída; confira e preencha os campos.'
        else:error='PDF salvo. Preencha os dados para vincular ao lançamento.'
        aid=str(extracted.get('account_id','50'))
        if aid not in ACCOUNT_MAP:aid='50'
        extracted_date=extracted.get('date')
        try:date.fromisoformat(extracted_date)
        except (ValueError,TypeError):extracted_date=f'{month}-01' if __import__('re').fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month) else date.today().isoformat()
        amount=extracted.get('amount')
        if not isinstance(amount,(float,int)) or amount<=0:amount=None
        record={'id':rid,'filename':file.filename,'storage_path':stored['path'],'content_type':mime,'size':len(data),'date':extracted_date,'category':ACCOUNT_MAP[aid]['group'],
            'amount':amount,'status':'pendente','transaction_id':None,'is_deleted':False,'created_at':datetime.now(timezone.utc).isoformat(),
            'extraction':{'description':str(extracted.get('description') or file.filename)[:250],'amount':amount,'date':extracted_date,'account_id':aid,'type':ACCOUNT_MAP[aid]['type'],'note':str(extracted.get('note') or '')[:2000]},'warning':error}
        await db.receipts.insert_one(record.copy())
        return {k:v for k,v in record.items() if k!='storage_path'}

    @router.get('/{rid}/file')
    async def receipt_file(rid:str):
        receipt=await db.receipts.find_one({'id':rid,'is_deleted':False},{'_id':0})
        if not receipt:raise HTTPException(404,'Comprovante não encontrado.')
        try:data=await run_in_threadpool(get_object,receipt['storage_path'])
        except Exception:raise HTTPException(503,'Não foi possível baixar o comprovante agora.')
        return Response(data,media_type=receipt['content_type'],headers={'Content-Disposition':f'inline; filename="comprovante-{rid}.{receipt["filename"].rsplit(".",1)[-1]}"','X-Content-Type-Options':'nosniff'})

    @router.delete('/{rid}')
    async def remove_receipt(rid:str):
        receipt=await db.receipts.find_one({'id':rid,'is_deleted':False},{'_id':0})
        if not receipt:raise HTTPException(404,'Comprovante não encontrado.')
        if receipt.get('transaction_id'):raise HTTPException(409,'Desvincule o lançamento antes de excluir o comprovante.')
        await db.receipts.update_one({'id':rid},{'$set':{'is_deleted':True}})
        return {'deleted':True}
    return router