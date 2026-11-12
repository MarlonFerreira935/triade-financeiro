import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from receipt_service import find_receipt, receipt_bytes, store_receipt


def create_receipt_router(db):
    router = APIRouter(prefix='/api/receipts')

    @router.get('')
    async def list_receipts(month: str = '', category: str = 'todas'):
        query = {'is_deleted': False}
        if month:
            query['date'] = {'$regex': '^' + re.escape(month)}
        if category != 'todas':
            query['category'] = category
        return await db.receipts.find(query, {'_id': 0, 'storage_path': 0}).sort('created_at', -1).to_list(1000)

    @router.post('', status_code=201)
    async def upload(file: UploadFile = File(...), month: str = Form('')):
        return await store_receipt(db, file, month)

    @router.get('/{rid}/file')
    async def receipt_file(rid: str):
        receipt = await find_receipt(db, rid)
        extension = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'application/pdf': 'pdf'}[receipt['content_type']]
        return Response(content=await receipt_bytes(receipt), media_type=receipt['content_type'], headers={
            'Content-Disposition': f'inline; filename="comprovante.{extension}"',
            'X-Content-Type-Options': 'nosniff',
        })

    @router.delete('/{rid}')
    async def remove_receipt(rid: str):
        receipt = await find_receipt(db, rid)
        if receipt.get('transaction_id'):
            raise HTTPException(409, 'Desvincule o lançamento antes de excluir o comprovante.')
        await db.receipts.update_one({'id': rid}, {'$set': {'is_deleted': True}})
        return {'deleted': True}

    return router