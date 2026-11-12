async def run_test(page, output_dir, page_url):
    import asyncio,json
    from urllib.parse import urlsplit,quote
    from playwright.async_api import expect
    base=urlsplit(page.url).scheme+'://'+urlsplit(page.url).netloc
    state={'mode':'failed_send','fail_b':True,'fail_list':False,'hold':None,'held':asyncio.Event(),'posts':[],'gets':[]}
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.get_by_test_id('period-select').wait_for(timeout=20000)
        month=await page.get_by_test_id('period-select').input_value()
        def conv(id,text):
            return {'id':id,'title':text,'month':month,'updated_at':'2026-10-01T12:00:00Z','messages':[{'id':id+'_u','role':'user','content':text,'status':'complete'},{'id':id+'_a','role':'assistant','content':text+' resposta servidor','status':'complete','month':month}]}
        a=conv('TEST_ONLY_A','TEST_ONLY A');b=conv('TEST_ONLY_B','TEST_ONLY B');done=conv('TEST_ONLY_done','TEST_ONLY_draft')
        details={x['id']:x for x in [a,b,done]}
        items=[{k:v for k,v in x.items() if k!='messages'} for x in [a,b]]
        async def guard(route):
            if route.request.method not in ['GET','HEAD','OPTIONS']: await route.abort();raise AssertionError('Unexpected write')
            await route.continue_()
        async def lists(route):
            hold=state['hold'];snapshot=list(items)
            if hold:
                state['held'].set();await hold.wait()
            if state['fail_list']: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY list503'}))
            else:
                try: await route.fulfill(status=200,content_type='application/json',body=json.dumps(snapshot))
                except Exception as e: print('Canceled old request '+type(e).__name__)
        async def detail_route(route):
            id=urlsplit(route.request.url).path.rsplit('/',1)[-1];state['gets'].append(id)
            if id==b['id'] and state['fail_b']: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY B503'}))
            else: await route.fulfill(status=200,content_type='application/json',body=json.dumps(details[id]))
        async def chat(route):
            state['posts'].append(route.request.post_data_json)
            events=[{'type':'meta','conversation_id':done['id'],'user_message_id':done['id']+'_u','updated_at':done['updated_at'],'month':month}]
            if state['mode']=='failed_send':events.append({'type':'error','message':'TEST_ONLY failed send'})
            else:
                events += [{'type':'delta','text':done['messages'][1]['content']},{'type':'done','conversation_id':done['id']}]
                state['fail_list']=True
            await route.fulfill(status=200,content_type='text/event-stream',body=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
        await page.route('**/api/**',guard)
        await page.route('**/api/advisor/conversations?*',lists)
        await page.route('**/api/advisor/conversations/*',detail_route)
        await page.route('**/api/advisor/chat',chat)
        await page.goto(base+'/consultor?pergunta=TEST_ONLY_draft',wait_until='domcontentloaded')
        await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled(timeout=20000)
        await page.get_by_test_id('advisor-send').click()
        await page.get_by_test_id('advisor-error').wait_for()
        await page.get_by_test_id('advisor-history-toggle').click()
        await page.get_by_test_id('conversation-select-TEST_ONLY_B').click()
        await expect(page.get_by_test_id('advisor-error')).to_contain_text('TEST_ONLY B503')
        state['fail_b']=False;n=len(state['gets'])
        await page.get_by_test_id('advisor-retry').click()
        await expect(page.get_by_test_id('chat-message-0')).to_contain_text('TEST_ONLY B')
        await expect(page.get_by_test_id('assistant-content-1')).to_have_text('TEST_ONLY B resposta servidor')
        assert state['gets'][n:]==[b['id']] and len(state['posts'])==1
        print('PASS selected B503 after failed send: retry GETs B, never resends old question')
        state['mode']='done';state['posts'].clear()
        await page.goto(base+'/consultor?pergunta=TEST_ONLY_draft',wait_until='domcontentloaded')
        await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled(timeout=20000)
        await page.get_by_test_id('advisor-send').click()
        await page.get_by_test_id('advisor-error').wait_for()
        state['fail_list']=False;state['hold']=asyncio.Event()
        await page.get_by_test_id('advisor-retry').click()
        await asyncio.wait_for(state['held'].wait(),5)
        await expect(page.get_by_test_id('assistant-content-1')).to_have_text(done['messages'][1]['content'])
        await expect(page.get_by_test_id('answer-source-1')).to_be_visible()
        assert await page.get_by_test_id('advisor-message-input').input_value()==''
        await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled()
        await page.get_by_test_id('advisor-message-input').fill('TEST_ONLY digitado DURANTE retry')
        print('PASS answer stays complete and composer usable WHILE history reload is delayed')
        await page.get_by_test_id('advisor-history-toggle').click()
        await page.get_by_test_id('conversation-select-TEST_ONLY_B').click()
        await expect(page.get_by_test_id('assistant-content-1')).to_have_text('TEST_ONLY B resposta servidor')
        state['hold'].set();state['hold']=None
        await page.wait_for_timeout(500)
        await expect(page.get_by_test_id('assistant-content-1')).to_have_text('TEST_ONLY B resposta servidor')
        assert await page.get_by_test_id('advisor-message-input').input_value()=='TEST_ONLY digitado DURANTE retry'
        assert len(state['posts'])==1
        print('PASS delayed reload aborted on selecting B: old done answer cannot overwrite B or new draft')
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL targeted history concurrency '+repr(e));raise
