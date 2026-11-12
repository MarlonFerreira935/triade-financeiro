"""Receipt faults, pure finance/export rules, and isolated advisor lifecycle regression."""
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import datetime, timezone

import pytest
import openpyxl
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import receipt_service as receipts
import advisor_chat_service as chats
from receipt_routes import create_receipt_router
from advisor_routes import create_advisor_router, ConsultInput
from finance import ACCOUNT_ROWS, ACCOUNT_MAP, TEMPLATE, group_for, totals, export_workbook, parse_workbook
from alert_rules import AlertContext, margin_drop_alert, is_material_increase, calculate_alerts

@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.parametrize('storage_result,status', [(b'TEST_file',200),(None,503),({'bytes':b'x'},503),(RuntimeError('TEST_storage'),503)])
def test_download_fault_paths(monkeypatch, storage_result, status):
    db = SimpleNamespace(receipts=SimpleNamespace(find_one=AsyncMock(return_value={'storage_path':'TEST_path','content_type':'image/png'})))
    def storage(_):
        if isinstance(storage_result, Exception):
            raise storage_result
        return storage_result
    monkeypatch.setattr(receipts, 'get_object', storage)
    app = FastAPI(); app.include_router(create_receipt_router(db))
    response = TestClient(app).get('/api/receipts/TEST_id/file')
    assert response.status_code == status
    if status == 200:
        assert response.content == storage_result
        assert response.headers['x-content-type-options'] == 'nosniff'
    else:
        assert 'baixar' in response.json()['detail']


def test_download_missing_record():
    db = SimpleNamespace(receipts=SimpleNamespace(find_one=AsyncMock(return_value=None)))
    app = FastAPI(); app.include_router(create_receipt_router(db))
    response = TestClient(app).get('/api/receipts/TEST_missing/file')
    assert response.status_code == 404
    assert 'não encontrado' in response.json()['detail']


def png():
    from PIL import Image
    content=io.BytesIO(); Image.new('RGB',(5,5),'white').save(content,format='PNG')
    return content.getvalue()


@pytest.mark.anyio
@pytest.mark.parametrize('filename,content,status',[('TEST.png',b'bad',400),('TEST.jpg',png(),400),('TEST.pdf',b'bad',400),('TEST.png',b'x'*(receipts.MAX_BYTES+1),413)],ids=['invalid-image','mime-mismatch','invalid-pdf','oversize'])
async def test_upload_invalid(filename,content,status):
    with pytest.raises(HTTPException) as error:
        await receipts.read_receipt_upload(UploadFile(filename=filename,file=io.BytesIO(content)))
    assert error.value.status_code == status
    assert isinstance(error.value.detail,str)


@pytest.mark.anyio
@pytest.mark.parametrize('filename,content,mime',[('TEST.png',png(),'image/png'),('TEST.pdf',b'%PDF-1.4 TEST','application/pdf')],ids=['image-ocr-fallback','pdf-manual'])
async def test_upload_initializes_content_and_manual_fallback(monkeypatch,filename,content,mime):
    db=SimpleNamespace(receipts=SimpleNamespace(insert_one=AsyncMock()))
    stored=[]
    def storage(path,data,kind):
        stored.append((data,kind)); return {'path':path}
    monkeypatch.setattr(receipts,'put_object',storage)
    monkeypatch.setattr(receipts,'extract_receipt',AsyncMock(side_effect=RuntimeError('TEST_ocr_down')))
    record=await receipts.store_receipt(db,UploadFile(filename=filename,file=io.BytesIO(content)),'2026-10')
    assert stored == [(content,mime)]
    assert record['status'] == 'pendente' and record['warning'] and record['amount'] is None
    assert record['extraction']['date']=='2026-10-01'
    assert 'storage_path' not in record
    assert db.receipts.insert_one.await_args.args[0]['size']==len(content)


@pytest.mark.parametrize('drop,severity',[(4.99,None),(5,'atencao'),(9.99,'atencao'),(10,'critico')])
def test_margin_boundary(drop,severity):
    current=totals([]); current.update(count=1,net_revenue=100,margin=20-drop)
    previous=totals([]); previous.update(count=1,net_revenue=100,margin=20)
    alert=margin_drop_alert(AlertContext('2026-10',current,previous))
    assert (alert['severity'] if alert else None)==severity


@pytest.mark.parametrize('value,previous,expected',[(3000,2500,True),(2999.99,2500,False),(1200,1000,False),(1500,1000,True),(10000,0,False)])
def test_expense_boundary(value,previous,expected):
    assert is_material_increase(value,previous) == expected


def record(row,amount):
    account=ACCOUNT_MAP[str(row)]
    return {'id':f'TEST_{row}','account_id':str(row),'amount':amount,'type':account['type'],'category':account['group'],
            'date':'2026-10-01','description':f'TEST_{row}','source':'manual'}


def test_original_formulas_and_all_45_groups():
    ranges=[(6,'Receitas'),(10,'Impostos e deduções'),(21,'Matéria-prima e insumos'),(27,'Logística e montagem'),
            (31,'Comissões'),(38,'Pessoal'),(45,'Ocupação e infraestrutura'),(50,'Administrativo e TI'),
            (54,'Marketing'),(57,'Frota e mobilidade'),(62,'Depreciação e provisões'),(66,'Resultado financeiro'),(999,'Sócios e investimentos')]
    assert len(ACCOUNT_ROWS)==45
    for row in ACCOUNT_ROWS:
        assert group_for(row)==next(name for limit,name in ranges if row<=limit)
    fixture=[record(row,row*11.13) for row in ACCOUNT_ROWS]
    t=totals(fixture)
    def summed(lo,hi): return round(sum(r['amount'] for r in fixture if lo<=int(r['account_id'])<=hi),2)
    net=round(summed(4,6)-summed(8,10),2)
    contribution=round(net-summed(14,31),2)
    ebitda=round(contribution-summed(36,57),2)
    profit=round(ebitda-summed(61,62)-summed(65,65)+summed(66,66),2)
    assert t['net_revenue']==net and t['contribution']==contribution and t['ebitda']==ebitda
    assert t['profit']==profit and t['free_cash']==round(profit-summed(70,72),2)
    assert t['margin']==round(profit/net*100,2)


def test_cash_withdrawals_equilibrium_and_no_data():
    empty=totals([])
    assert calculate_alerts('2026-10',empty,empty,[],[])==[]
    fixture=[record(4,10000),record(14,5000),record(36,6000),record(70,2000)]
    t=totals(fixture)
    assert t['profit']==-1000 and t['free_cash']==-3000 and t['break_even']==12000
    alerts={a['rule']:a for a in calculate_alerts('2026-10',t,empty,fixture,[])}
    assert {'negative_cash','withdrawals','break_even','low_margin'}<=alerts.keys()
    positive=[record(4,10000),record(70,1500)]
    assert 'withdrawals' not in {a['rule'] for a in calculate_alerts('2026-10',totals(positive),empty,positive,[])}
    positive[-1]['amount']=1500.01
    assert 'withdrawals' in {a['rule'] for a in calculate_alerts('2026-10',totals(positive),empty,positive,[])}


def test_export_original_sheets_formulas_styles_and_ledger():
    original=openpyxl.load_workbook(TEMPLATE)
    fixture=[record(4,1234.56)]
    exported=openpyxl.load_workbook(io.BytesIO(export_workbook(fixture,2026)))
    assert len(original.sheetnames)==14
    assert exported.sheetnames==original.sheetnames+['Lançamentos do Sistema']
    assert exported['DRE Gerencial'].cell(4,11).value==1234.56
    for sheet in original:
        for row in sheet:
            for cell in row:
                target=exported[sheet.title][cell.coordinate]
                if cell.data_type=='f': assert target.value==cell.value
                assert target.style_id==cell.style_id
    assert exported['Lançamentos do Sistema']['B2'].value=='TEST_4'
    assert exported['Lançamentos do Sistema'].freeze_panes=='A2'
    assert parse_workbook(TEMPLATE.read_bytes(),2099)[0]['date'].startswith('2099-')


@pytest.mark.anyio
async def test_retry_reuses_question_and_validates_content():
    original={'id':'TEST_user','conversation_id':'TEST_conversation','role':'user','content':'TEST_question'}
    collection=SimpleNamespace(find_one=AsyncMock(side_effect=[original,None]),insert_one=AsyncMock())
    service=chats.AdvisorChatService(SimpleNamespace(advisor_messages=collection))
    data=ConsultInput(message='TEST_question',month='2026-10',conversation_id='TEST_conversation',retry_message_id='TEST_user')
    result=await service.user_message('TEST_conversation',data,datetime.now(timezone.utc))
    assert result==original
    collection.insert_one.assert_not_awaited()
    assert collection.find_one.await_args_list[0].args[0]['content']=='TEST_question'
    collection.find_one=AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as error: await service.user_message('TEST_other',data,datetime.now(timezone.utc))
    assert error.value.status_code==400
    collection.find_one=AsyncMock(side_effect=[original,{'id':'TEST_complete'}])
    with pytest.raises(HTTPException) as error: await service.user_message('TEST_conversation',data,datetime.now(timezone.utc))
    assert error.value.status_code==409


@pytest.mark.anyio
@pytest.mark.parametrize('failed',[False,True])
async def test_advisor_stream_persists_and_releases(monkeypatch,failed):
    async def generator(*args):
        yield 'TEST_answer'
        if failed: raise RuntimeError('TEST_failure')
    monkeypatch.setattr(chats,'consult',generator)
    collection=SimpleNamespace(insert_one=AsyncMock())
    conversations=SimpleNamespace(update_one=AsyncMock())
    service=chats.AdvisorChatService(SimpleNamespace(advisor_messages=collection,conversations=conversations))
    request=chats.ChatRequest('TEST_c','TEST_request',{'id':'TEST_user'},{'updated_at':'TEST_time','month':'2026-10','totals':{'count':1}},[],'TEST_question')
    events=[json.loads(e[6:]) async for e in service.events(request)]
    assert events[0]['user_message_id']=='TEST_user'
    assert events[-1]['type']==('error' if failed else 'done')
    saved=collection.insert_one.await_args.args[0]
    assert saved['content']=='TEST_answer' and saved['reply_to']=='TEST_user'
    assert saved['status']==('failed' if failed else 'complete')
    assert conversations.update_one.await_args.args[0]=={'id':'TEST_c','request_id':'TEST_request'}


def test_soft_delete_preserves_messages():
    messages=SimpleNamespace(delete_many=AsyncMock())
    conversations=SimpleNamespace(find_one=AsyncMock(return_value={'id':'TEST_c'}),update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1)))
    db=SimpleNamespace(conversations=conversations,advisor_messages=messages)
    app=FastAPI(); app.include_router(create_advisor_router(db))
    response=TestClient(app).delete('/api/advisor/conversations/TEST_c')
    assert response.status_code==200 and response.json()=={'deleted':True}
    assert conversations.update_one.await_args.args[1]['$set']['is_deleted'] is True
    assert conversations.find_one.await_args.args[0]['is_deleted']=={'$ne':True}
    messages.delete_many.assert_not_awaited()


@pytest.mark.anyio
async def test_no_data_guard_does_not_call_gemini(monkeypatch):
    import advisor_service
    client=AsyncMock(side_effect=AssertionError('must not call Gemini'))
    monkeypatch.setattr(advisor_service,'chat',client)
    text=''.join([s async for s in advisor_service.consult({'month':'2099-01','totals':{'count':0}},[],'TEST_question')])
    assert '01/2099' in text and 'Não há lançamentos' in text
    client.assert_not_called()


@pytest.mark.anyio
async def test_import_uses_fake_db_and_preserves_manual_records(monkeypatch):
    import server
    transactions=SimpleNamespace(update_one=AsyncMock(),delete_many=AsyncMock())
    imports=SimpleNamespace(insert_one=AsyncMock())
    monkeypatch.setattr(server,'db',SimpleNamespace(transactions=transactions,imports=imports))
    data=await server.import_sheet(UploadFile(filename='TEST_original.xlsx',file=io.BytesIO(TEMPLATE.read_bytes())),2099)
    expected=parse_workbook(TEMPLATE.read_bytes(),2099)
    assert data['count']==len(expected) and data['year']==2099
    assert transactions.update_one.await_count==len(expected)
    deletion=transactions.delete_many.await_args.args[0]
    assert deletion['source']=='planilha' and deletion['date']=={'$regex':'^2099-'}
    assert set(deletion['id']['$nin'])=={r['id'] for r in expected}
    # This is a fake DB only; exported audit workbooks must be rejected before writes.
    transactions.update_one.reset_mock()
    exported=export_workbook([record(4,100)],2099)
    with pytest.raises(HTTPException) as error:
        await server.import_sheet(UploadFile(filename='TEST_export.xlsx',file=io.BytesIO(exported)),2099)
    assert error.value.status_code==400 and 'Reimportação bloqueada' in error.value.detail
    transactions.update_one.assert_not_awaited()