async def run_test(page, output_dir, page_url):
    import json
    from urllib.parse import urlsplit
    base=urlsplit(page.url).scheme+'://'+urlsplit(page.url).netloc
    state={'fail_list':False,'posts':0,'list_calls':0}
    cid='TEST_ONLY_postdone'
    stamp='2026-10-01T12:00:00+00:00'
    conversations=[]
    details={}
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.get_by_test_id('period-select').wait_for(timeout=20000)
        month=await page.get_by_test_id('period-select').input_value()
        async def fake_list(route):
            state['list_calls']+=1
            if state['fail_list']: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY postdone history503'}))
            else: await route.fulfill(status=200,content_type='application/json',body=json.dumps(conversations))
        async def fake_detail(route):
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(details))
        async def fake_chat(route):
            state['posts']+=1
            data=json.loads(route.request.post_data)
            details.update({'id':cid,'title':data['message'],'month':month,'updated_at':stamp,'messages':[{'id':'TEST_ONLY_u','role':'user','content':data['message'],'status':'complete'},{'id':'TEST_ONLY_a','role':'assistant','content':'TEST_ONLY completed answer','status':'complete','month':month}]})
            conversations.append({k:v for k,v in details.items() if k!='messages'})
            state['fail_list']=True
            events=[{'type':'meta','conversation_id':cid,'user_message_id':'TEST_ONLY_u','updated_at':stamp,'month':month},{'type':'delta','text':'TEST_ONLY completed answer'},{'type':'done','conversation_id':cid,'assistant_id':'TEST_ONLY_a'}]
            await route.fulfill(status=200,content_type='text/event-stream',body=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
        await page.route('**/api/advisor/conversations?*',fake_list)
        await page.route('**/api/advisor/conversations/*',fake_detail)
        await page.route('**/api/advisor/chat',fake_chat)
        await page.goto(base+'/consultor',wait_until='domcontentloaded')
        await page.get_by_test_id('advisor-message-input').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        await page.get_by_test_id('advisor-message-input').fill('TEST_ONLY postdone protection')
        await page.get_by_test_id('advisor-send').click(force=True)
        await page.get_by_test_id('advisor-error').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert 'histórico não pôde' in await page.get_by_test_id('advisor-error').inner_text()
        assert await page.get_by_test_id('answer-source-1').is_visible()
        assert await page.get_by_test_id('answer-incomplete-1').count()==0
        assert 'TEST_ONLY completed answer' in await page.get_by_test_id('assistant-content-1').inner_text()
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140156_9581882332c7/iteration4-advisor-postdone-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS: done answer remains complete after subsequent conversation-list503')
        before=state['list_calls']
        state['fail_list']=False
        await page.get_by_test_id('advisor-retry').click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert state['list_calls']>before
        assert state['posts']==1
        assert 'TEST_ONLY completed answer' in await page.get_by_test_id('assistant-content-1').inner_text()
        assert await page.get_by_test_id('advisor-error').count()==0
        assert await page.get_by_test_id('answer-incomplete-1').count()==0
        print('PASS: retry loads completed history, no second chat POST; MOCKED TEST ONLY')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(600)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140156_9581882332c7/iteration4-advisor-mobile.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS: advisor mobile no overflow')
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL postdone: '+repr(e))
        raise
