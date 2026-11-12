async def run_test(page, output_dir, page_url):
    import json,uuid
    await page.set_viewport_size({'width':1920,'height':800})
    base=page.url.split('/')[0]+'//'+page.url.split('/')[2]
    results=[]
    tid=None;cid=None
    baseline=(await (await page.request.get(base+'/api/transactions')).json())
    try:
        await page.goto(base+'/lancamentos')
        await page.get_by_test_id('ledger-count').wait_for(timeout=15000)
        month=await page.get_by_test_id('period-select').input_value()
        before=(await (await page.request.get(base+'/api/dashboard?month='+month)).json())['totals']
        refreshed=[]
        page.on('request',lambda req: refreshed.append(req.url) if any('/api/'+part in req.url for part in ['meta','dashboard','alerts']) else None)
        await page.get_by_test_id('new-transaction').click(force=True)
        assert await page.get_by_test_id('transaction-account-select').locator('option').count()==41
        await page.get_by_test_id('transaction-type-income').click(force=True)
        assert await page.get_by_test_id('transaction-account-select').locator('option').count()==4
        await page.get_by_test_id('transaction-type-expense').click(force=True)
        desc='TEST_UI_quality_'+uuid.uuid4().hex[:8]
        await page.get_by_test_id('transaction-description-input').fill(desc)
        await page.get_by_test_id('transaction-amount-input').fill('1.23')
        await page.get_by_test_id('transaction-account-select').select_option('50',force=True)
        await page.wait_for_timeout(200)
        async with page.expect_response(lambda r:'/api/transactions' in r.url and r.request.method=='POST') as posted:
            await page.get_by_test_id('transaction-save').click(force=True)
        response=await posted.value;data=await response.json();tid=data.get('id')
        assert response.status==201 and tid
        await page.get_by_test_id('transaction-description-'+tid).wait_for(timeout=15000)
        after=(await (await page.request.get(base+'/api/dashboard?month='+month)).json())['totals']
        assert round(after['profit'],2)==round(before['profit']-1.23,2)
        assert all(any('/api/'+part in url for url in refreshed) for part in ['meta','dashboard','alerts'])
        print('PASS transaction expense/income filters, real save, financial recalculation and workspace refresh')
        results.append({'test':'transaction save/refresh','passed':True})
        await page.get_by_test_id('delete-transaction-'+tid).click(force=True)
        await page.get_by_test_id('delete-confirm').click(force=True)
        await page.get_by_test_id('transaction-description-'+tid).wait_for(state='hidden',timeout=15000)
        remaining=await (await page.request.get(base+'/api/transactions')).json()
        assert tid not in [t['id'] for t in remaining]
        tid=None
        assert sorted(remaining,key=lambda r:r['id'])==sorted(baseline,key=lambda r:r['id'])
        print('PASS exact test transaction deleted; all original financial records unchanged')
        results.append({'test':'original finance preserved','passed':True})
    except Exception as e:
        print('FAIL transaction regression',str(e));results.append({'test':'transaction save/refresh','passed':False,'error':str(e)})
    finally:
        if tid: print('CLEANUP test transaction', (await page.request.delete(base+'/api/transactions/'+tid)).status)
    try:
        await page.goto(base+'/consultor')
        await page.get_by_test_id('advisor-message-input').wait_for(timeout=15000)
        await page.get_by_test_id('advisor-new-chat').click(force=True)
        question='TEST_UI_chat_'+uuid.uuid4().hex[:8]+': Resuma o resultado deste mês em uma frase.'
        await page.get_by_test_id('advisor-message-input').fill(question)
        async with page.expect_response(lambda r:'/api/advisor/chat' in r.url and r.request.method=='POST',timeout=150000) as stream:
            await page.get_by_test_id('advisor-send').click(force=True)
        response=await stream.value
        body=await response.text()
        for line in body.splitlines():
            if line.startswith('data: '):
                event=json.loads(line[6:])
                if event.get('conversation_id'): cid=event['conversation_id']
        assert cid
        await page.get_by_test_id('answer-source-1').wait_for(timeout=150000)
        await page.get_by_test_id('advisor-new-chat').wait_for(state='visible')
        await page.wait_for_timeout(500)
        assert await page.get_by_test_id('advisor-new-chat').is_enabled()
        stored=await (await page.request.get(base+'/api/advisor/conversations/'+cid)).json()
        assert len(stored['messages'])==2 and stored['messages'][0]['content']==question and stored['messages'][1]['status']=='complete'
        print('PASS actual Gemini frontend SSE completes and two messages persist')
        results.append({'test':'real frontend Gemini/persistence','passed':True})
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
        print('PASS conversation confirmation cancel/delete and soft-deleted history exclusion')
        results.append({'test':'conversation delete confirmation','passed':True})
    except Exception as e:
        print('FAIL actual chat regression',str(e));results.append({'test':'real chat/delete','passed':False,'error':str(e)})
    finally:
        if cid: print('CLEANUP own conversation softdelete', (await page.request.delete(base+'/api/advisor/conversations/'+cid)).status)
    try:
        await page.goto(base+'/comprovantes')
        await page.get_by_test_id('receipts-all-months').click(force=True)
        await page.locator('[data-testid^="preview-receipt-"]').first.wait_for(timeout=15000)
        await page.locator('[data-testid^="preview-receipt-"]').first.click(force=True)
        await page.get_by_test_id('receipt-preview-modal').wait_for()
        image=page.get_by_test_id('receipt-preview-modal').locator('img')
        if await image.count(): assert await image.evaluate('(img)=>img.complete && img.naturalWidth>0')
        await page.keyboard.press('Escape')
        print('PASS existing receipt viewer read-only')
        results.append({'test':'receipt viewer','passed':True})
        await page.goto(base+'/dre')
        await page.get_by_test_id('dre-comparison-view').click(force=True)
        await page.get_by_test_id('dre-toggle-detail').click(force=True)
        await page.get_by_test_id('dre-toggle-detail').click(force=True)
        assert await page.get_by_test_id('dre-original-structure').is_visible()
        print('PASS DRE comparison and detail controls')
        results.append({'test':'DRE controls','passed':True})
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_135206_5d3e467ad6f4/t1-dre-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        await page.goto(base+'/')
        await page.get_by_test_id('chart-cumulative').click(force=True)
        await page.wait_for_timeout(2500)
        assert 'active' in await page.get_by_test_id('chart-cumulative').get_attribute('class')
        await page.get_by_test_id('chart-monthly').click(force=True)
        await page.wait_for_timeout(2500)
        assert await page.get_by_test_id('expenses-donut').is_visible()
        print('PASS monthly/cumulative and donut chart controls')
        results.append({'test':'dashboard chart controls','passed':True})
    except Exception as e:
        print('FAIL read-only UI regression',str(e));results.append({'test':'read-only UI','passed':False,'error':str(e)})
    try:
        await page.set_viewport_size({'width':390,'height':844})
        for screen in ['consultor','dre','comprovantes','lancamentos','alertas']:
            await page.goto(base+'/'+screen)
            await page.get_by_test_id('period-select').wait_for(timeout=15000)
            await page.wait_for_timeout(2500)
            overflow=await page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
            assert not overflow,screen+' horizontal overflow'
            print('PASS mobile no overflow',screen)
        await page.goto(base+'/consultor')
        await page.get_by_test_id('advisor-name').wait_for(timeout=15000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_135206_5d3e467ad6f4/t1-consultor-mobile.jpeg', type="jpeg", quality=40, full_page=False)
        await page.get_by_test_id('open-sidebar').click(force=True)
        await page.get_by_test_id('nav-dre').click(force=True)
        await page.get_by_test_id('dre-original-structure').wait_for(timeout=15000)
        assert not await page.get_by_test_id('sidebar-backdrop').count()
        print('PASS mobile menu navigation')
        results.append({'test':'mobile navigation/layout','passed':True})
    except Exception as e:
        print('FAIL mobile regression',str(e));results.append({'test':'mobile navigation/layout','passed':False,'error':str(e)})
    print('UI_RESULTS',json.dumps(results))
    error_text=await page.evaluate('''() => {const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', ');}''')
    print('Found error message: '+error_text if error_text else 'No error messages found on the page')
