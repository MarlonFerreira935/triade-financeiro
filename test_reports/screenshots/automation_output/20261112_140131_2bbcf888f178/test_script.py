async def run_test(page, output_dir, page_url):
    import json
    from urllib.parse import urlsplit, quote
    base=urlsplit(page.url).scheme+'://'+urlsplit(page.url).netloc
    posts=[]
    page.on('request',lambda req: posts.append(req.url) if '/api/advisor/chat' in req.url and req.method=='POST' else None)
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.get_by_test_id('period-select').wait_for(timeout=20000)
        month=await page.get_by_test_id('period-select').input_value()
        real_list=await (await page.request.get(base+'/api/advisor/conversations?month='+month)).json()
        fail_list=True
        calls=[]
        async def initial_list(route):
            calls.append(route.request.url)
            if fail_list: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY initial history503'}))
            else: await route.continue_()
        await page.route('**/api/advisor/conversations?*',initial_list)
        await page.goto(base+'/consultor',wait_until='domcontentloaded')
        await page.get_by_test_id('advisor-error').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140131_2bbcf888f178/iteration4-advisor-history-error-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        before=len(calls)
        fail_list=False
        await page.get_by_test_id('advisor-retry').click(force=True)
        await page.get_by_test_id('advisor-error').wait_for(state='detached',timeout=15000)
        await page.wait_for_timeout(600)
        assert len(calls)>before
        assert await page.get_by_test_id('advisor-message-input').is_enabled()
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        for item in real_list:
            assert await page.get_by_test_id('conversation-select-'+item['id']).is_visible()
        assert len(posts)==0
        print('PASS: initial list503 retry issues fresh GET, restores real history, no chat POST')
        await page.unroute('**/api/advisor/conversations?*',initial_list)
        draft='TEST_ONLY draft preserved after URL clean'
        await page.goto(base+'/consultor?pergunta='+quote(draft),wait_until='domcontentloaded')
        await page.get_by_test_id('advisor-message-input').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert 'pergunta=' not in page.url
        assert await page.get_by_test_id('advisor-message-input').input_value()==draft
        assert len(posts)==0
        print('PASS: incoming question draft preserved after query removal')
    except Exception as e:
        print('FAIL initial history/draft: '+repr(e))
        raise
    try:
        aid='TEST_ONLY_A'; bid='TEST_ONLY_B'; cid='TEST_ONLY_C'
        stamp='2026-10-01T12:00:00+00:00'
        conversations=[{'id':aid,'title':'TEST_ONLY older conversation','month':month,'updated_at':stamp},{'id':bid,'title':'TEST_ONLY selected target','month':month,'updated_at':stamp}]
        details={x['id']:{**x,'messages':[{'id':x['id']+'_u','role':'user','content':x['title'],'status':'complete'},{'id':x['id']+'_a','role':'assistant','content':'TEST_ONLY response '+x['id'],'status':'complete','month':month}]} for x in conversations}
        selected_fails=True
        list_fails=False
        get_calls=[]
        mode='failed'
        async def fake_list(route):
            get_calls.append('list')
            if list_fails: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY post-done list503'}))
            else: await route.fulfill(status=200,content_type='application/json',body=json.dumps(conversations))
        async def fake_detail(route):
            target=route.request.url.rsplit('/',1)[-1]
            get_calls.append(target)
            if target==bid and selected_fails: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY selected history503'}))
            else: await route.fulfill(status=200,content_type='application/json',body=json.dumps(details[target]))
        async def fake_chat(route):
            nonlocal_dummy=None
            global list_fails, conversations
            data=json.loads(route.request.post_data)
            if mode=='failed':
                events=[{'type':'meta','conversation_id':'TEST_ONLY_failed','user_message_id':'TEST_ONLY_user','updated_at':stamp,'month':month},{'type':'delta','text':'TEST_ONLY incomplete'},{'type':'error','message':'TEST_ONLY stream failed'}]
            else:
                details[cid]={'id':cid,'title':data['message'],'month':month,'updated_at':stamp,'messages':[{'id':'TEST_ONLY_C_u','role':'user','content':data['message'],'status':'complete'},{'id':'TEST_ONLY_C_a','role':'assistant','content':'TEST_ONLY completed answer','status':'complete','month':month}]}
                conversations.insert(0,{k:v for k,v in details[cid].items() if k!='messages'})
                list_fails=True
                events=[{'type':'meta','conversation_id':cid,'user_message_id':'TEST_ONLY_C_u','updated_at':stamp,'month':month},{'type':'delta','text':'TEST_ONLY completed answer'},{'type':'done','conversation_id':cid,'assistant_id':'TEST_ONLY_C_a'}]
            await route.fulfill(status=200,content_type='text/event-stream',body=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
        await page.route('**/api/advisor/conversations?*',fake_list)
        await page.route('**/api/advisor/conversations/*',fake_detail)
        await page.route('**/api/advisor/chat',fake_chat)
        await page.goto(base+'/consultor',wait_until='domcontentloaded')
        await page.get_by_test_id('answer-source-1').wait_for(timeout=15000)
        await page.get_by_test_id('advisor-new-chat').click(force=True)
        await page.get_by_test_id('advisor-message-input').fill('TEST_ONLY prior failed question never resend')
        await page.get_by_test_id('advisor-send').click(force=True)
        await page.get_by_test_id('answer-incomplete-1').wait_for(timeout=15000)
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        await page.get_by_test_id('conversation-select-'+bid).click(force=True)
        await page.get_by_test_id('advisor-error').wait_for(timeout=15000)
        assert 'selected history503' in await page.get_by_test_id('advisor-error').inner_text()
        selected_fails=False
        old_posts=len(posts)
        old_target_calls=get_calls.count(bid)
        await page.get_by_test_id('advisor-retry').click(force=True)
        await page.get_by_test_id('assistant-content-1').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert 'TEST_ONLY response '+bid in await page.get_by_test_id('assistant-content-1').inner_text()
        assert get_calls.count(bid)>old_target_calls
        assert len(posts)==old_posts
        assert await page.get_by_test_id('advisor-error').count()==0
        print('PASS: selected conversation503 retry gets exact target B, not A or prior question; zero retry POST')
        mode='complete'
        await page.get_by_test_id('advisor-new-chat').click(force=True)
        await page.get_by_test_id('advisor-message-input').fill('TEST_ONLY post-done history protection')
        await page.get_by_test_id('advisor-send').click(force=True)
        await page.get_by_test_id('advisor-error').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert 'histórico não pôde' in await page.get_by_test_id('advisor-error').inner_text()
        assert await page.get_by_test_id('answer-source-1').is_visible()
        assert await page.get_by_test_id('answer-incomplete-1').count()==0
        assert 'TEST_ONLY completed answer' in await page.get_by_test_id('assistant-content-1').inner_text()
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140131_2bbcf888f178/iteration4-advisor-postdone-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        old_posts=len(posts)
        old_lists=get_calls.count('list')
        list_fails=False
        await page.get_by_test_id('advisor-retry').click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert get_calls.count('list')>old_lists
        assert len(posts)==old_posts
        assert 'TEST_ONLY completed answer' in await page.get_by_test_id('assistant-content-1').inner_text()
        assert await page.get_by_test_id('advisor-error').count()==0
        assert await page.get_by_test_id('answer-incomplete-1').count()==0
        print('PASS: done answer stays complete after list503; retry restores history without resending')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(600)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140131_2bbcf888f178/iteration4-advisor-mobile.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS: advisor desktop/mobile no overflow; all simulated chat POSTs MOCKED TEST ONLY')
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL selected history/postdone: '+repr(e))
        raise
