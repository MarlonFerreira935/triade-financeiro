async def run_test(page, output_dir, page_url):
    import asyncio, json
    from urllib.parse import urlsplit
    base = urlsplit(page.url).scheme + '://' + urlsplit(page.url).netloc
    mutations = []
    page.on('request', lambda req: mutations.append(req.method+' '+req.url) if '/api/' in req.url and req.method not in ['GET','HEAD','OPTIONS'] else None)
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.get_by_test_id('page-title').wait_for(timeout=20000)
        month = await page.get_by_test_id('period-select').input_value()
        baseline = await (await page.request.get(base+'/api/alerts?month='+month)).json()
        fail_alerts = True
        calls = []
        async def alerts_handler(route):
            calls.append(route.request.url)
            if fail_alerts: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY alerts unavailable'}))
            else: await route.continue_()
        await page.route('**/api/alerts?*',alerts_handler)
        await page.goto(base+'/alertas',wait_until='domcontentloaded')
        await page.get_by_test_id('alerts-load-error').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert await page.get_by_test_id('alerts-retry').is_visible()
        assert await page.get_by_test_id('page-loading').count()==0
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140042_10a9fbda668f/iteration4-alerts-error-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(600)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140042_10a9fbda668f/iteration4-alerts-error-mobile.jpeg', type="jpeg", quality=40, full_page=False)
        fail_alerts=False
        before=len(calls)
        await page.get_by_test_id('alerts-retry').click(force=True)
        await page.get_by_test_id('alert-total-count').wait_for(timeout=15000)
        assert len(calls)>before
        for testid,key in [('alert-total-count','count'),('alert-critical-count','critical_count'),('alert-unread-count','unread_count')]:
            assert (await page.get_by_test_id(testid).inner_text()).split()[0]==str(baseline[key])
        after=await (await page.request.get(base+'/api/alerts?month='+month)).json()
        assert [(x['id'],x['acknowledged']) for x in baseline['alerts']]==[(x['id'],x['acknowledged']) for x in after['alerts']]
        assert not mutations, mutations
        print('PASS: alerts503 error/retry restores real summary; acknowledgments unchanged; zero API writes; desktop/mobile no overflow')
        await page.unroute('**/api/alerts?*',alerts_handler)
    except Exception as e:
        print('FAIL alerts: '+repr(e))
        raise
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        history=await (await page.request.get(base+'/api/spreadsheet/history')).json()
        hold=asyncio.Event()
        async def delayed_history(route):
            await hold.wait()
            await route.continue_()
        await page.route('**/api/spreadsheet/history',delayed_history)
        await page.goto(base+'/planilhas',wait_until='domcontentloaded')
        await page.get_by_test_id('spreadsheet-history-loading').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert await page.get_by_test_id('spreadsheet-history-loading').get_attribute('role')=='status'
        assert await page.get_by_test_id('spreadsheet-name').is_visible()
        assert await page.get_by_test_id('spreadsheet-upload').is_enabled()
        assert await page.get_by_test_id('page-loading').count()==0
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140042_10a9fbda668f/iteration4-spreadsheet-loading-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS: local history loading status; page stays available')
        hold.set()
        await page.get_by_test_id('spreadsheet-history-loading').wait_for(state='detached',timeout=15000)
        for i,item in enumerate(history):
            assert item['filename'] in await page.get_by_test_id('import-history-'+str(i)).inner_text()
        print('PASS: all existing import history rows loaded after delay')
        await page.unroute('**/api/spreadsheet/history',delayed_history)
        fail_history=True
        calls=[]
        async def history_handler(route):
            calls.append(route.request.url)
            if fail_history: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY history unavailable'}))
            else: await route.continue_()
        await page.route('**/api/spreadsheet/history',history_handler)
        await page.reload(wait_until='domcontentloaded')
        await page.get_by_test_id('spreadsheet-history-error').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(600)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.get_by_test_id('spreadsheet-history-retry').scroll_into_view_if_needed()
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140042_10a9fbda668f/iteration4-spreadsheet-error-mobile.jpeg', type="jpeg", quality=40, full_page=False)
        fail_history=False
        before=len(calls)
        await page.get_by_test_id('spreadsheet-history-retry').click(force=True)
        await page.get_by_test_id('spreadsheet-history-error').wait_for(state='detached',timeout=15000)
        if history:
            await page.get_by_test_id('import-history-0').wait_for(timeout=15000)
            assert history[0]['filename'] in await page.get_by_test_id('import-history-0').inner_text()
        assert len(calls)>before
        assert not mutations, mutations
        print('PASS: spreadsheet503 retry restores real history; zero API writes; mobile no overflow')
        await page.unroute('**/api/spreadsheet/history',history_handler)
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL spreadsheet: '+repr(e))
        raise
