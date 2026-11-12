async def run_test(page, output_dir, page_url):
    import json,asyncio
    await page.set_viewport_size({'width':1920,'height':800})
    base=page.url.split('/')[0]+'//'+page.url.split('/')[2]
    results=[]
    try:
        deleted=[]
        item={'id':'TEST_delete_dialog','title':'TEST_delete_dialog_question','updated_at':'2026-10-01T00:00:00Z','month':'2026-10'}
        async def fake_history(route): await route.fulfill(status=200,content_type='application/json',body=json.dumps([item]))
        async def fake_detail(route):
            if route.request.method=='DELETE':
                deleted.append(route.request.url);body={'deleted':True}
            else: body={**item,'messages':[{'id':'TEST_msg','role':'user','content':'TEST_delete_dialog_question','status':'complete'}]}
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(body))
        await page.route('**/api/advisor/conversations?*',fake_history)
        await page.route('**/api/advisor/conversations/TEST_delete_dialog',fake_detail)
        await page.goto(base+'/consultor')
        await page.get_by_test_id('advisor-message-input').wait_for(timeout=15000)
        await page.wait_for_timeout(400)
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        await page.get_by_test_id('conversation-delete-TEST_delete_dialog').click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for()
        await page.wait_for_timeout(200)
        await page.get_by_test_id('delete-conversation-cancel').click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for(state='hidden',timeout=5000)
        await page.wait_for_timeout(200)
        assert not deleted
        await page.get_by_test_id('conversation-delete-TEST_delete_dialog').click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for()
        await page.wait_for_timeout(200)
        await page.get_by_test_id('delete-conversation-confirm').click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for(state='hidden',timeout=5000)
        assert len(deleted)==1
        assert await page.get_by_test_id('conversation-select-TEST_delete_dialog').count()==0
        print('PASS conversation delete cancel/confirm (TEST ONLY stub, animation waits)')
        results.append({'test':'delete confirmation with settled animation','passed':True})
    except Exception as e:
        print('FAIL delete confirmation',repr(e));results.append({'test':'delete confirmation','passed':False,'error':repr(e)})
    finally:
        await page.unroute('**/api/advisor/conversations?*',fake_history)
        await page.unroute('**/api/advisor/conversations/TEST_delete_dialog',fake_detail)
    try:
        acknowledged=False;put=[]
        async def fake_alerts(route):
            a={'id':'TEST_alert','title':'TEST_alert_title','description':'TEST_alert_description','action':'TEST_next_step','metric':'R$ 1,00','severity':'critico','acknowledged':acknowledged}
            feed={'month':'2026-10','updated_at':'2026-10-01T00:00:00Z','alerts':[a],'rules':[],'count':1,'critical_count':1,'unread_count':0 if acknowledged else 1,'has_data':True}
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(feed))
        async def fake_ack(route):
            nonlocal_error=None
            put.append(route.request.post_data_json)
            await route.fulfill(status=200,content_type='application/json',body='{"id":"TEST_alert","acknowledged":true}')
        await page.route('**/api/alerts?*',fake_alerts)
        await page.route('**/api/alerts/TEST_alert/acknowledge',fake_ack)
        await page.goto(base+'/alertas')
        await page.get_by_test_id('alerts-filter-critical').click(force=True)
        assert await page.get_by_test_id('financial-alert-TEST_alert').is_visible()
        await page.get_by_test_id('alerts-filter-unread').click(force=True)
        await page.get_by_test_id('alert-rules-toggle').click(force=True)
        async with page.expect_response(lambda r:'/TEST_alert/acknowledge' in r.url) as ack:
            await page.get_by_test_id('alert-acknowledge-TEST_alert').click(force=True)
        await ack.value
        acknowledged=True
        await page.wait_for_timeout(500)
        assert len(put)==1 and put[0]=={'month':'2026-10','acknowledged':True}
        print('PASS alert filters/rules and acknowledge payload without changing real acknowledgements')
        results.append({'test':'alert filters/ack payload','passed':True})
    except Exception as e:
        print('FAIL alerts regression',repr(e));results.append({'test':'alert filters/ack','passed':False,'error':repr(e)})
    finally:
        await page.unroute('**/api/alerts?*',fake_alerts)
        await page.unroute('**/api/alerts/TEST_alert/acknowledge',fake_ack)
    try:
        started=asyncio.Event()
        async def history_delay(route):
            started.set();await asyncio.sleep(1.8)
            try: await route.fulfill(status=200,content_type='application/json',body='[]')
            except Exception: pass
        await page.route('**/api/spreadsheet/history',history_delay)
        await page.goto(base+'/planilhas')
        await asyncio.wait_for(started.wait(),timeout=15000)
        await page.get_by_test_id('spreadsheet-name').wait_for(timeout=15000)
        print('OBSERVED spreadsheet history loading indication:',await page.get_by_test_id('page-loading').count())
        results.append({'test':'spreadsheet history loading indication','passed':await page.get_by_test_id('page-loading').count()>0})
    except Exception as e: print('FAIL spreadsheet loading probe',repr(e))
    finally: await page.unroute('**/api/spreadsheet/history',history_delay)
    print('UI_RESULTS',json.dumps(results))
