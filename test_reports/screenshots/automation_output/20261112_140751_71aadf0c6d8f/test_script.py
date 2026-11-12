async def run_test(page, output_dir, page_url):
    import asyncio, json
    from urllib.parse import urlsplit, quote, parse_qs
    from playwright.async_api import expect
    base = urlsplit(page.url).scheme+'://'+urlsplit(page.url).netloc
    results=[]
    state={'fail_list':False,'fail_detail':None,'send_fail':False,'postdone_fail':False,'posts':[],'gets':[],'lists':0,'hold':None,'held':None}
    question='TEST_ONLY_draft'
    answer='TEST_ONLY resposta completa preservada'
    cid='TEST_ONLY_completed'
    month=''
    conversations=[]
    details={}
    def detail(id,text):
        return {'id':id,'title':text,'month':month,'updated_at':'2026-10-01T12:00:00Z','messages':[{'id':id+'_u','role':'user','content':text,'status':'complete'},{'id':id+'_a','role':'assistant','content':answer if id==cid else text+' resposta','status':'complete','month':month}]}
    async def mock_list(route):
        state['lists']+=1
        snapshot=list(conversations)
        hold=state['hold']
        if hold:
            state['held'].set()
            await hold.wait()
        if state['fail_list']:
            await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY lista503'}))
        else:
            try: await route.fulfill(status=200,content_type='application/json',body=json.dumps(snapshot))
            except Exception as e: print('Canceled delayed route:',type(e).__name__)
    async def mock_detail(route):
        id=urlsplit(route.request.url).path.rsplit('/',1)[-1]
        state['gets'].append(id)
        if state['fail_detail']==id:
            await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY conversa503'}))
        else:
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(details[id]))
    async def mock_chat(route):
        payload=route.request.post_data_json
        state['posts'].append(payload)
        details[cid]=detail(cid,payload['message'])
        conversations[:]=[{k:v for k,v in details[cid].items() if k!='messages'}]
        events=[{'type':'meta','conversation_id':cid,'user_message_id':cid+'_u','updated_at':'2026-10-01T12:00:00Z','month':month}]
        if state['send_fail']: events.append({'type':'error','message':'TEST_ONLY envio falhou'})
        else: events += [{'type':'delta','text':answer},{'type':'done','conversation_id':cid}]
        if state['postdone_fail']: state['fail_list']=True
        await route.fulfill(status=200,content_type='text/event-stream',body=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
    async def block_write(route):
        if route.request.method not in ['GET','HEAD','OPTIONS']:
            raise AssertionError('Unexpected real API write '+route.request.url)
        await route.continue_()
    async def open_chat(draft=''):
        await page.goto(base+'/consultor'+('?pergunta='+quote(draft) if draft else ''),wait_until='domcontentloaded')
        await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled(timeout=20000)
    async def check_answer(draft=''):
        await expect(page.get_by_test_id('assistant-content-1')).to_have_text(answer)
        await expect(page.get_by_test_id('answer-source-1')).to_be_visible()
        assert await page.locator('[data-testid^="chat-message-"]').count()==2
        assert await page.get_by_test_id('advisor-message-input').input_value()==draft
    async def scenario(name,action):
        try:
            await action()
            results.append({'name':name,'pass':True})
            print('PASS '+name)
        except Exception as e:
            results.append({'name':name,'pass':False,'error':repr(e)})
            print('FAIL '+name+' '+repr(e))
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.get_by_test_id('period-select').wait_for(timeout=20000)
        month=await page.get_by_test_id('period-select').input_value()
        await page.route('**/api/**',block_write)
        await page.route('**/api/advisor/conversations?*',mock_list)
        await page.route('**/api/advisor/conversations/*',mock_detail)
        await page.route('**/api/advisor/chat',mock_chat)
        async def combined():
            conversations.clear(); state['fail_list']=False;state['postdone_fail']=True;state['posts'].clear()
            await open_chat(question)
            assert 'pergunta=' not in page.url
            assert await page.get_by_test_id('advisor-message-input').input_value()==question
            await page.get_by_test_id('advisor-send').click()
            await page.get_by_test_id('advisor-error').wait_for()
            await check_answer()
            state['fail_list']=False
            before=len(state['gets'])
            await page.get_by_test_id('advisor-retry').click()
            await page.get_by_test_id('advisor-error').wait_for(state='detached')
            await expect(page.get_by_test_id('chat-message-0')).to_contain_text(question)
            await page.wait_for_timeout(350)
            await check_answer()
            assert state['gets'][before:]==[cid]
            assert len(state['posts'])==1
            await page.screenshot(path=output_dir+'/iteration5-combined-desktop.jpeg', type='jpeg', quality=40, full_page=False)
        await scenario('combined incoming draft -> SSEdone -> list503 -> retry: answer retained, server pair, empty composer, one POST',combined)
        async def new_draft():
            conversations.clear();state['fail_list']=False;state['posts'].clear()
            await open_chat(question)
            await page.get_by_test_id('advisor-send').click()
            await page.get_by_test_id('advisor-error').wait_for()
            await page.get_by_test_id('advisor-message-input').fill('TEST_ONLY NOVO rascunho')
            state['fail_list']=False
            await page.get_by_test_id('advisor-retry').click()
            await page.wait_for_timeout(350)
            await check_answer('TEST_ONLY NOVO rascunho')
            assert len(state['posts'])==1
            await page.set_viewport_size({'width':390,'height':844})
            await page.wait_for_timeout(350)
            assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            await page.screenshot(path=output_dir+'/iteration5-combined-mobile.jpeg', type='jpeg', quality=40, full_page=False)
            await page.set_viewport_size({'width':1920,'height':800})
            assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await scenario('postdone recovery preserves NEW draft; desktop/mobile no overflow',new_draft)
        async def initial(draft):
            state['postdone_fail']=False;state['fail_list']=True;state['posts'].clear();state['gets'].clear()
            await open_chat(draft)
            await page.get_by_test_id('advisor-error').wait_for()
            assert await page.get_by_test_id('advisor-message-input').input_value()==draft
            state['fail_list']=False
            n=state['lists']
            await page.get_by_test_id('advisor-retry').click()
            await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled()
            await page.wait_for_timeout(350)
            assert state['lists']>n and not state['posts']
            assert await page.get_by_test_id('advisor-message-input').input_value()==draft
            if draft:
                assert not state['gets']
                assert await page.locator('[data-testid^="chat-message-"]').count()==0
            else:
                assert state['gets']==[cid]
                await check_answer()
        await scenario('initial list503 WITHOUT draft: GET retry opens latest, no POST',lambda:initial(''))
        await scenario('initial list503 WITH incoming draft: GET retry preserves draft, no POST',lambda:initial(question))
        async def send_retry():
            conversations.clear();state['fail_list']=False;state['posts'].clear();state['send_fail']=True
            await open_chat(question)
            await page.get_by_test_id('advisor-send').click()
            await page.get_by_test_id('advisor-error').wait_for()
            await expect(page.get_by_test_id('answer-incomplete-1')).to_be_visible()
            state['send_fail']=False
            await page.get_by_test_id('advisor-retry').click()
            await expect(page.get_by_test_id('answer-source-1')).to_be_visible()
            await check_answer()
            assert len(state['posts'])==2
            assert state['posts'][0]['message']==state['posts'][1]['message']==question
            assert state['posts'][1]['retry_message_id']==cid+'_u'
            assert await page.locator('.chat-message.user').count()==1
        await scenario('failed send retry reuses original/server user id; one user bubble',send_retry)
        async def selected():
            details['TEST_ONLY_B']=detail('TEST_ONLY_B','TEST_ONLY B target')
            conversations.append({k:v for k,v in details['TEST_ONLY_B'].items() if k!='messages'})
            await open_chat()
            state['posts'].clear();state['fail_detail']='TEST_ONLY_B'
            await page.get_by_test_id('advisor-history-toggle').click()
            await page.get_by_test_id('conversation-select-TEST_ONLY_B').click()
            await page.get_by_test_id('advisor-error').wait_for()
            state['fail_detail']=None
            before=len(state['gets'])
            await page.get_by_test_id('advisor-retry').click()
            await expect(page.get_by_test_id('chat-message-0')).to_contain_text('TEST_ONLY B target')
            assert state['gets'][before:]==['TEST_ONLY_B'] and not state['posts']
        await scenario('selected conversation503 retries exact B target without POST',selected)
        async def delayed_navigation():
            state['fail_list']=True
            await open_chat()
            await page.get_by_test_id('advisor-error').wait_for()
            state['fail_list']=False;state['hold']=asyncio.Event();state['held']=asyncio.Event()
            await page.get_by_test_id('advisor-retry').click()
            await asyncio.wait_for(state['held'].wait(),5)
            await page.get_by_test_id('advisor-history-toggle').click()
            # Initial list failed, so navigate by new-chat to invalidate the reload.
            await page.get_by_test_id('advisor-new-chat').click()
            await page.get_by_test_id('advisor-message-input').fill('TEST_ONLY contexto novo')
            state['hold'].set();state['hold']=None
            await page.wait_for_timeout(500)
            assert await page.locator('[data-testid^="chat-message-"]').count()==0
            assert await page.get_by_test_id('advisor-message-input').input_value()=='TEST_ONLY contexto novo'
        await scenario('delayed history reload aborted by new conversation cannot overwrite new context',delayed_navigation)
        async def delayed_month():
            state['fail_list']=True
            await open_chat()
            await page.get_by_test_id('advisor-error').wait_for()
            state['fail_list']=False;state['hold']=asyncio.Event();state['held']=asyncio.Event()
            await page.get_by_test_id('advisor-retry').click()
            await asyncio.wait_for(state['held'].wait(),5)
            options=await page.get_by_test_id('period-select').locator('option').evaluate_all('(els)=>els.map(x=>x.value)')
            next_month=next(x for x in options if x and x!=month)
            # The old handler keeps its captured event and response; new-month list is empty.
            old=state['hold'];state['hold']=None;conversations.clear()
            await page.get_by_test_id('period-select').select_option(next_month)
            await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled(timeout=20000)
            await page.get_by_test_id('advisor-message-input').fill('TEST_ONLY novo mês')
            old.set()
            await page.wait_for_timeout(500)
            assert await page.get_by_test_id('period-select').input_value()==next_month
            assert await page.locator('[data-testid^="chat-message-"]').count()==0
            assert await page.get_by_test_id('advisor-message-input').input_value()=='TEST_ONLY novo mês'
            await page.get_by_test_id('period-select').select_option(month)
        await scenario('delayed history old-month response cannot overwrite changed month',delayed_month)
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
        print('RESULTS '+json.dumps(results))
    except Exception as e:
        print('FAIL test setup '+repr(e))
        raise
