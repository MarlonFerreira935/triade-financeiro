async def run_test(page, output_dir, page_url):
    import uuid
    from urllib.parse import urlsplit
    from playwright.async_api import expect
    base=urlsplit(page.url).scheme+'://'+urlsplit(page.url).netloc
    cid=None
    deleted=False
    delete_requests=[]
    question='TEST_UI_SETTLED_DELETE_'+uuid.uuid4().hex[:10]+': Resuma a margem em uma frase.'
    page.on('request',lambda req: delete_requests.append(req.url) if req.method=='DELETE' and '/api/advisor/conversations/' in req.url else None)
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.goto(base+'/consultor',wait_until='domcontentloaded')
        await expect(page.get_by_test_id('advisor-message-input')).to_be_enabled(timeout=20000)
        month=await page.get_by_test_id('period-select').input_value()
        await page.get_by_test_id('advisor-new-chat').click(force=True)
        await page.get_by_test_id('advisor-message-input').fill(question)
        await page.get_by_test_id('advisor-send').click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=150000)
        await expect(page.get_by_test_id('advisor-history-toggle')).to_be_enabled(timeout=150000)
        assert len(await page.get_by_test_id('assistant-content-1').inner_text())>20
        items=await (await page.request.get(base+'/api/advisor/conversations?month='+month)).json()
        own=[x for x in items if x['title']==question[:80]]
        assert len(own)==1
        cid=own[0]['id']
        print('OWN_TEMP_CONVERSATION_ID='+cid)
        persisted=await (await page.request.get(base+'/api/advisor/conversations/'+cid)).json()
        assert len(persisted['messages'])==2
        assert persisted['messages'][0]['content']==question
        assert persisted['messages'][1]['status']=='complete'
        print('PASS: own real UI Gemini SSE completed and persisted')
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        await page.get_by_test_id('conversation-select-'+cid).click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=20000)
        assert question in await page.get_by_test_id('chat-message-0').inner_text()
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        await page.get_by_test_id('conversation-delete-'+cid).click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for(timeout=10000)
        await page.wait_for_timeout(600)
        await page.get_by_test_id('delete-conversation-cancel').click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for(state='hidden',timeout=10000)
        await page.wait_for_timeout(600)
        assert not delete_requests
        assert (await page.request.get(base+'/api/advisor/conversations/'+cid)).status==200
        print('PASS: cancel sends no DELETE and preserves own conversation')
        await page.get_by_test_id('conversation-delete-'+cid).click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for(timeout=10000)
        await page.wait_for_timeout(600)
        assert await page.get_by_test_id('delete-conversation-confirm').is_enabled()
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140333_8fd03c37f566/iteration4-real-delete-dialog-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        await page.get_by_test_id('delete-conversation-confirm').dblclick(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for(state='hidden',timeout=15000)
        await page.wait_for_timeout(600)
        assert await page.get_by_test_id('conversation-select-'+cid).count()==0
        assert await page.get_by_test_id('conversation-delete-'+cid).count()==0
        assert delete_requests==[base+'/api/advisor/conversations/'+cid],delete_requests
        assert (await page.request.get(base+'/api/advisor/conversations/'+cid)).status==404
        visible=await (await page.request.get(base+'/api/advisor/conversations?month='+month)).json()
        assert cid not in [x['id'] for x in visible]
        deleted=True
        assert await page.locator('[data-sonner-toast][data-type="error"]').count()==0
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        print('PASS: settled real UI cancel/reopen/confirm succeeds; double-click sends one DELETE; list/get hide own id; no false error')
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL settled real UI delete: '+repr(e))
        raise
    finally:
        if cid and not deleted:
            clean=await page.request.delete(base+'/api/advisor/conversations/'+cid)
            print('Own exact-ID cleanup status='+str(clean.status))
        elif cid:
            print('Own exact-ID cleanup already completed through UI: '+cid)
