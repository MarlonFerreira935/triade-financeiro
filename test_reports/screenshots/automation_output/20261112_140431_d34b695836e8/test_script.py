async def run_test(page, output_dir, page_url):
    import json
    from urllib.parse import urlsplit, quote
    from playwright.async_api import expect
    base=urlsplit(page.url).scheme+'://'+urlsplit(page.url).netloc
    state={'fail':False,'posts':0,'lists':0}
    question='TEST_ONLY incoming draft postdone history'
    cid='TEST_ONLY_incoming_completed'
    conversations=[]
    details={}
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.get_by_test_id('period-select').wait_for(timeout=20000)
        month=await page.get_by_test_id('period-select').input_value()
        async def fake_list(route):
            state['lists']+=1
            if state['fail']: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY history503'}))
            else: await route.fulfill(status=200,content_type='application/json',body=json.dumps(conversations))
        async def fake_detail(route):
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(details))
        async def fake_chat(route):
            state['posts']+=1
            details.update({'id':cid,'title':question,'month':month,'updated_at':'2026-10-01T12:00:00Z','messages':[{'id':'TEST_ONLY_draft_u','role':'user','content':question,'status':'complete'},{'id':'TEST_ONLY_draft_a','role':'assistant','content':'TEST_ONLY completed incoming draft answer','status':'complete','month':month}]})
            conversations.append({k:v for k,v in details.items() if k!='messages'})
            state['fail']=True
            events=[{'type':'meta','conversation_id':cid,'user_message_id':'TEST_ONLY_draft_u','updated_at':'2026-10-01T12:00:00Z','month':month},{'type':'delta','text':'TEST_ONLY completed incoming draft answer'},{'type':'done','conversation_id':cid}]
            await route.fulfill(status=200,content_type='text/event-stream',body=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
        await page.route('**/api/advisor/conversations?*',fake_list)
        await page.route('**/api/advisor/conversations/*',fake_detail)
        await page.route('**/api/advisor/chat',fake_chat)
        await page.goto(base+'/consultor?pergunta='+quote(question),wait_until='domcontentloaded')
        await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled(timeout=15000)
        assert 'pergunta=' not in page.url
        assert await page.get_by_test_id('advisor-message-input').input_value()==question
        await page.get_by_test_id('advisor-send').click(force=True)
        await page.get_by_test_id('advisor-error').wait_for(timeout=15000)
        assert await page.get_by_test_id('answer-source-1').is_visible()
        state['fail']=False
        before=state['lists']
        await page.get_by_test_id('advisor-retry').click(force=True)
        await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled(timeout=15000)
        await page.wait_for_timeout(600)
        assert state['lists']>before
        assert state['posts']==1
        sources=await page.get_by_test_id('answer-source-1').count()
        message_count=await page.locator('[data-testid^="chat-message-"]').count()
        current_draft=await page.get_by_test_id('advisor-message-input').input_value()
        print('Incoming draft retry result: answer_sources='+str(sources)+', messages='+str(message_count)+', old draft restored='+str(current_draft==question)+', posts='+str(state['posts']))
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        assert await page.get_by_test_id('conversation-select-'+cid).is_visible()
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140431_d34b695836e8/iteration4-incoming-draft-retry-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        if sources==0:
            print('FAIL: postdone history retry with incoming ?pergunta clears completed answer and restores sent draft; list recovered and no POST resend')
        else:
            print('PASS: incoming question postdone retry preserves completed answer')
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL incoming draft recovery test: '+repr(e))
        raise
