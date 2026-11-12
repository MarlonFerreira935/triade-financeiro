"""Read-only production API consistency plus exclusively test-owned soft-deleted chat."""
import io
import json
import os
import uuid
from pathlib import Path
import sys
import requests
import openpyxl
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
BASE_URL=os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from finance import totals


def get(path):
    response=requests.get(f'{BASE_URL}/api{path}',timeout=45)
    assert response.status_code==200, response.text[:250]
    return response


def test_readonly_financial_consistency():
    assert get('/').json()['status']=='ok'
    meta=get('/meta').json()
    assert len(meta['accounts'])==45
    month=meta['default_month']; year=month[:4]
    records=get('/transactions').json()
    baseline=Path('/app/test_reports/t1-financial-baseline.json')
    if not baseline.exists():
        baseline.write_text(json.dumps(records,ensure_ascii=False))
    dashboard=get(f'/dashboard?month={month}').json()
    monthly=[r for r in records if r['date'].startswith(month)]
    assert dashboard['totals']==totals(monthly)
    dre=get(f'/dre?year={year}').json()
    assert dre['totals']==totals([r for r in records if r['date'].startswith(year+'-')])
    assert next(r for r in dre['rows'] if r['row']==67)['values'][int(month[-2:])-1]==dashboard['totals']['profit']
    assert get(f'/alerts?month={month}').json()['month']==month
    assert isinstance(get(f'/receipts?month={month}').json(),list)
    assert isinstance(get('/spreadsheet/history').json(),list)
    assert isinstance(get(f'/advisor/conversations?month={month}').json(),list)
    assert 'text' in get(f'/diagnostics/latest?month={month}').json()
    original=openpyxl.load_workbook(io.BytesIO(get('/spreadsheet/original').content))
    exported=openpyxl.load_workbook(io.BytesIO(get(f'/spreadsheet/export?year={year}').content))
    assert exported.sheetnames==original.sheetnames+['Lançamentos do Sistema']


def test_real_gemini_complete_persist_retry_and_soft_delete():
    month=get('/meta').json()['default_month']
    question=f'TEST_quality_{uuid.uuid4().hex[:8]}: Resuma a margem deste mês em uma frase.'
    cid=None
    try:
        response=requests.post(f'{BASE_URL}/api/advisor/chat',json={'month':month,'message':question},stream=True,timeout=150)
        assert response.status_code==200,response.text[:250]
        events=[]
        for line in response.iter_lines():
            if line.startswith(b'data: '):
                event=json.loads(line[6:]); events.append(event)
                if event.get('conversation_id'): cid=event['conversation_id']
        assert events[-1]['type']=='done',events
        text=''.join(e.get('text','') for e in events)
        assert len(text)>20
        saved=get(f'/advisor/conversations/{cid}').json()
        user=next(m for m in saved['messages'] if m['role']=='user')
        assistant=next(m for m in saved['messages'] if m['role']=='assistant')
        assert user['content']==question and assistant['content']==text and assistant['status']=='complete'
        retry=requests.post(f'{BASE_URL}/api/advisor/chat',json={'month':month,'message':question,'conversation_id':cid,'retry_message_id':user['id']},timeout=45)
        assert retry.status_code==409 and 'já foi respondida' in retry.json()['detail']
        assert len(get(f'/advisor/conversations/{cid}').json()['messages'])==2
    finally:
        if cid:
            deleted=requests.delete(f'{BASE_URL}/api/advisor/conversations/{cid}',timeout=45)
            assert deleted.status_code==200 and deleted.json()['deleted'] is True
            assert requests.get(f'{BASE_URL}/api/advisor/conversations/{cid}',timeout=30).status_code==404
            assert cid not in [c['id'] for c in get(f'/advisor/conversations?month={month}').json()]


def test_financial_snapshot_is_unchanged():
    baseline=json.loads(Path('/app/test_reports/t1-financial-baseline.json').read_text())
    actual=get('/transactions').json()
    assert sorted(actual,key=lambda record:record['id'])==sorted(baseline,key=lambda record:record['id'])