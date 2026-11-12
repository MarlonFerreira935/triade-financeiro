async def run_test(page, output_dir, page_url):
    import json,uuid
    await page.set_viewport_size({'width':1920,'height':800})
    base=page.url.split('/')[0]+'//'+page.url.split('/')[2]
    results=[]
    cid=None;tid=None
    try:
        month=(await (await page.request.get(base+'/api/meta')).json())['default_month']
        owned_question='TEST_UI_chat_d89e8660: Resuma o resultado deste mês em uma frase.'
        conversations=await (await page.request.get(base+'/api/advisor/conversations?month='+month)).json()
        own=next(c for c in conversations if c['title']==owned_question)
        cid=own['id']
        saved=await (await page.request.get(base+'/api/advisor/conversations/'+cid)).json()
        assert len(saved['messages'])==2 and saved['messages'][0]['content']==owned_question and saved['messages'][1]['status']=='complete'
        await page.goto(base+'/consultor')
        await page.get_by_test_id('advisor-message-input').wait_for(timeout=15000)
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        await page.get_by_test_id('conversation-select-'+cid).click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=15000)
        assert await page.get_by_test_id('assistant-content-1').inner_text()
        print('PASS actual frontend Gemini answer persisted, reopened through history')
        results.append({'test':'actual frontend Gemini/history persistence','passed':True})
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        await page.get_by_test_id('conversation-delete-'+cid).click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for()
        await page.get_by_test_id('delete-conversation-cancel').click(force=True)
        assert (await page.request.get(base+'/api/advisor/conversations/'+cid)).status==200
        await page.get_by_test_id('conversation-delete-'+cid).click(force=True)
        await page.get_by_test_id('delete-conversation-confirm').click(force=True)
        await page.get_by_test_id('delete-conversation-modal').wait_for(state='hidden',timeout=15000)
        assert (await page.request.get(base+'/api/advisor/conversations/'+cid)).status==404
        assert await page.get_by_test_id('conversation-select-'+cid).count()==0
        cid=None
        print('PASS conversation delete cancel/confirm and history exclusion')
        results.append({'test':'conversation delete confirmation','passed':True})
    except Exception as e:
        print('FAIL own chat cleanup/history',repr(e));results.append({'test':'history/delete','passed':False,'error':str(e)})
    finally:
        if cid: print('CLEANUP exact own conversation:',(await page.request.delete(base+'/api/advisor/conversations/'+cid)).status)
    try:
        baseline=await (await page.request.get(base+'/api/transactions')).json()
        await page.goto(base+'/lancamentos')
        await page.get_by_test_id('ledger-count').wait_for(timeout=15000)
        await page.get_by_test_id('new-transaction').click(force=True)
        await page.get_by_test_id('transaction-description-input').fill('TEST_delete_check_'+uuid.uuid4().hex[:8])
        await page.get_by_test_id('transaction-amount-input').fill('1.23')
        async with page.expect_response(lambda r:'/api/transactions' in r.url and r.request.method=='POST') as posted:
            await page.get_by_test_id('transaction-save').click(force=True)
        data=await (await posted.value).json();tid=data['id']
        await page.get_by_test_id('transaction-modal').wait_for(state='hidden',timeout=10000)
        await page.get_by_test_id('transaction-description-'+tid).wait_for(timeout=15000)
        await page.wait_for_timeout(700)
        await page.get_by_test_id('delete-transaction-'+tid).scroll_into_view_if_needed()
        await page.get_by_test_id('delete-transaction-'+tid).click(force=True)
        await page.get_by_test_id('delete-transaction-modal').wait_for(timeout=5000)
        await page.get_by_test_id('delete-confirm').click(force=True)
        await page.get_by_test_id('delete-transaction-modal').wait_for(state='hidden',timeout=10000)
        remaining=await (await page.request.get(base+'/api/transactions')).json()
        assert tid not in [r['id'] for r in remaining]
        tid=None
        assert sorted(remaining,key=lambda r:r['id'])==sorted(baseline,key=lambda r:r['id'])
        print('PASS real transaction deletion and full financial preservation')
        results.append({'test':'transaction delete/financial preservation','passed':True})
    except Exception as e:
        print('FAIL delete regression',repr(e));results.append({'test':'transaction delete','passed':False,'error':str(e)})
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_135345_b26ef4ed004d/t1-delete-check.jpeg', type="jpeg", quality=40, full_page=False)
    finally:
        if tid: print('CLEANUP exact own transaction:',(await page.request.delete(base+'/api/transactions/'+tid)).status)
    try:
        await page.goto(base+'/comprovantes')
        await page.get_by_test_id('receipts-all-months').click(force=True)
        await page.locator('[data-testid^="preview-receipt-"]').first.wait_for(timeout=15000)
        await page.locator('[data-testid^="preview-receipt-"]').first.click(force=True)
        await page.get_by_test_id('receipt-preview-modal').wait_for()
        await page.wait_for_function('()=>{const img=document.querySelector("[data-testid=receipt-preview-modal] img");return !img || (img.complete && img.naturalWidth>0)}',timeout=15000)
        await page.keyboard.press('Escape')
        print('PASS receipt list and original image viewer')
        results.append({'test':'receipt list/viewer','passed':True})
    except Exception as e:
        print('FAIL receipt viewer',repr(e));results.append({'test':'receipt viewer','passed':False,'error':str(e)})
    try:
        await page.goto(base+'/dre')
        await page.get_by_test_id('dre-comparison-view').click(force=True)
        await page.get_by_test_id('dre-toggle-detail').click(force=True)
        await page.get_by_test_id('dre-toggle-detail').click(force=True)
        assert await page.get_by_test_id('dre-original-structure').is_visible()
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_135345_b26ef4ed004d/t1-dre-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS DRE comparison/detail controls')
        results.append({'test':'DRE controls','passed':True})
        await page.goto(base+'/')
        await page.get_by_test_id('chart-cumulative').click(force=True)
        await page.wait_for_timeout(2500)
        assert 'active' in await page.get_by_test_id('chart-cumulative').get_attribute('class')
        await page.get_by_test_id('chart-monthly').click(force=True)
        await page.wait_for_timeout(2500)
        assert await page.get_by_test_id('expenses-donut').is_visible()
        print('PASS chart monthly/cumulative/donut')
        results.append({'test':'chart modes/donut','passed':True})
        await page.set_viewport_size({'width':390,'height':844})
        await page.goto(base+'/consultor')
        await page.get_by_test_id('advisor-name').wait_for(timeout=15000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_135345_b26ef4ed004d/t1-consultor-mobile-clean.jpeg', type="jpeg", quality=40, full_page=False)
        await page.get_by_test_id('open-sidebar').click(force=True)
        await page.wait_for_timeout(400)
        await page.get_by_test_id('nav-dre').click(force=True)
        await page.get_by_test_id('dre-original-structure').wait_for(timeout=15000)
        await page.wait_for_timeout(400)
        assert await page.get_by_test_id('sidebar-backdrop').count()==0
        print('PASS mobile menu after opening animation')
        results.append({'test':'mobile menu','passed':True})
    except Exception as e:
        print('FAIL DRE/charts/mobile',repr(e));results.append({'test':'DRE/charts/mobile','passed':False,'error':str(e)})
    print('UI_RESULTS',json.dumps(results))
    error_text=await page.evaluate('''() => {const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', ');}''')
    print('Found error message: '+error_text if error_text else 'No error messages found on the page')
