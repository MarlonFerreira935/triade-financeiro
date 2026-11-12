async def run_test(page, output_dir, page_url):
    import asyncio,json
    from urllib.parse import urlparse,parse_qs
    await page.set_viewport_size({'width':1920,'height':800})
    base=page.url.split('/')[0]+'//'+page.url.split('/')[2]
    results=[]
    async def empty_history(route): await route.fulfill(status=200,content_type='application/json',body='[]')
    await page.route('**/api/advisor/conversations?*',empty_history)
    try:
        await page.goto(base+'/consultor?pergunta=TEST_draft_survives')
        await page.get_by_test_id('advisor-message-input').wait_for(timeout=15000)
        await page.wait_for_timeout(500)
        assert await page.get_by_test_id('advisor-message-input').input_value()=='TEST_draft_survives'
        assert 'pergunta' not in page.url
        print('PASS query draft survives URL clearing')
        results.append({'test':'query draft','passed':True})
        payloads=[]
        async def fake_chat(route):
            payloads.append(route.request.post_data_json)
            meta={'type':'meta','conversation_id':'TEST_stub_chat','user_message_id':'TEST_server_user','updated_at':'2026-10-01T10:00:00Z','month':payloads[-1]['month'],'record_count':1}
            events=[meta,{'type':'error','message':'TEST_stream_failure'}] if len(payloads)==1 else [meta,{'type':'delta','text':'TEST_retry_answer'},{'type':'done','conversation_id':'TEST_stub_chat'}]
            await asyncio.sleep(.4)
            await route.fulfill(status=200,content_type='text/event-stream',body=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
        await page.route('**/api/advisor/chat',fake_chat)
        await page.get_by_test_id('advisor-send').evaluate('(e)=>{e.click();e.click()}')
        await page.get_by_test_id('advisor-error').wait_for(timeout=10000)
        assert len(payloads)==1
        await page.get_by_test_id('advisor-retry').click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=10000)
        assert len(payloads)==2 and payloads[1]['retry_message_id']=='TEST_server_user'
        assert await page.locator('.chat-message.user').count()==1
        assert await page.get_by_test_id('assistant-content-1').inner_text()=='TEST_retry_answer'
        print('PASS duplicate-click lock and retry uses server user id without duplicate user message')
        results.append({'test':'duplicate/retry','passed':True})
        await page.get_by_test_id('advisor-new-chat').click(force=True)
        await page.get_by_test_id('advisor-suggestion-0').click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=10000)
        assert len(payloads)==3
        print('PASS suggestion send')
        results.append({'test':'suggestion send','passed':True})
        await page.unroute('**/api/advisor/chat',fake_chat)
    except Exception as e:
        print('FAIL advisor draft/duplicate/retry',str(e));results.append({'test':'advisor draft/duplicate/retry','passed':False,'error':str(e)})
    finally: await page.unroute('**/api/advisor/conversations?*',empty_history)
    try:
        history_started=asyncio.Event()
        async def fake_list(route): await route.fulfill(status=200,content_type='application/json',body='[{"id":"TEST_history","title":"TEST_title","updated_at":"2026-10-01T00:00:00Z"}]')
        async def delayed_history(route):
            history_started.set();await asyncio.sleep(1.8)
            try: await route.fulfill(status=200,content_type='application/json',body='{"id":"TEST_history","messages":[{"id":"TEST_old","role":"assistant","status":"complete","content":"TEST_OLD_HISTORY"}]}')
            except Exception: pass
        await page.route('**/api/advisor/conversations?*',fake_list)
        await page.route('**/api/advisor/conversations/TEST_history',delayed_history)
        await page.goto(base+'/consultor')
        await asyncio.wait_for(history_started.wait(),timeout=15)
        await page.get_by_test_id('advisor-new-chat').click(force=True)
        await page.get_by_test_id('advisor-welcome-title').wait_for(timeout=10000)
        await page.wait_for_timeout(2200)
        assert await page.get_by_text('TEST_OLD_HISTORY',exact=True).count()==0
        assert await page.get_by_test_id('advisor-message-input').is_enabled()
        print('PASS new chat cancels delayed history overwrite')
        results.append({'test':'new chat/history race','passed':True})
    except Exception as e:
        print('FAIL history race',str(e));results.append({'test':'new chat/history race','passed':False,'error':str(e)})
    finally:
        await page.unroute('**/api/advisor/conversations?*',fake_list)
        await page.unroute('**/api/advisor/conversations/TEST_history',delayed_history)
    try:
        calls=[]
        async def fail_history(route):
            calls.append(route.request.url);await route.fulfill(status=503,content_type='application/json',body='{"detail":"TEST_history_failure"}')
        await page.route('**/api/advisor/conversations?*',fail_history)
        await page.goto(base+'/consultor')
        await page.get_by_test_id('advisor-error').wait_for(timeout=15000)
        before=len(calls)
        await page.get_by_test_id('advisor-retry').click(force=True)
        await page.wait_for_timeout(700)
        recovered=await page.get_by_test_id('advisor-error').count()==0
        print('OBSERVED initial history retry: requests before/after',before,len(calls),'recovered',recovered)
        results.append({'test':'initial history error retry','passed':recovered,'before':before,'after':len(calls)})
    except Exception as e: print('FAIL initial history error retry',str(e))
    finally: await page.unroute('**/api/advisor/conversations?*',fail_history)
    print('UI_RESULTS',json.dumps(results))
    error_text=await page.evaluate('''() => {const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', ');}''')
    print('Found error message: '+error_text if error_text else 'No error messages found on the page')
