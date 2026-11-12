async def run_test(page, output_dir, page_url):
    import asyncio, json
    from urllib.parse import urlsplit
    base = urlsplit(page.url).scheme + '://' + urlsplit(page.url).netloc
    results = []
    mutations = []
    page.on('request', lambda req: mutations.append(req.url) if req.method not in ['GET','HEAD','OPTIONS'] else None)
    try:
        await page.set_viewport_size({'width': 1920, 'height': 800})
        await page.get_by_test_id('page-title').wait_for(timeout=20000)
        print('PASS: frontend loads')
        month = await page.get_by_test_id('period-select').input_value()
        response = await page.request.get(base + '/api/alerts?month=' + month)
        baseline = await response.json()
        fail_alerts = True
        alert_calls = []
        async def alerts_handler(route):
            alert_calls.append(route.request.url)
            if fail_alerts:
                await route.fulfill(status=503, content_type='application/json', body=json.dumps({'detail':'TEST_ONLY alerts unavailable'}))
            else:
                await route.continue_()
        await page.route('**/api/alerts?*', alerts_handler)
        await page.goto(base + '/alertas', wait_until='domcontentloaded')
        await page.get_by_test_id('alerts-load-error').wait_for(timeout=20000)
        await page.wait_for_timeout(600)
        assert await page.get_by_test_id('alerts-retry').is_visible()
        assert await page.get_by_test_id('page-loading').count() == 0
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140016_6e7c1b2c157a/iteration4-alerts-error-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS: alerts503 error + retry, no infinite spinner, desktop no overflow')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(600)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140016_6e7c1b2c157a/iteration4-alerts-error-mobile.jpeg', type="jpeg", quality=40, full_page=False)
        fail_alerts = False
        before = len(alert_calls)
        await page.get_by_test_id('alerts-retry').click(force=True)
        await page.get_by_test_id('alert-total-count').wait_for(timeout=15000)
        assert len(alert_calls) > before
        for testid, key in [('alert-total-count','count'),('alert-critical-count','critical_count'),('alert-unread-count','unread_count')]:
            assert (await page.get_by_test_id(testid).inner_text()).split()[0] == str(baseline[key])
        after = await (await page.request.get(base + '/api/alerts?month=' + month)).json()
        assert [(x['id'],x['acknowledged']) for x in baseline['alerts']] == [(x['id'],x['acknowledged']) for x in after['alerts']]
        assert not mutations
        print('PASS: real alerts retry restores correct counts and acknowledgments unchanged; zero write requests')
        await page.unroute('**/api/alerts?*',alerts_handler)
    except Exception as e:
        print('FAIL alerts scenario: ' + str(e))
        raise
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        history = await (await page.request.get(base + '/api/spreadsheet/history')).json()
        hold = asyncio.Event()
        async def delayed_history(route):
            await hold.wait()
            await route.continue_()
        await page.route('**/api/spreadsheet/history',delayed_history)
        await page.goto(base + '/planilhas',wait_until='domcontentloaded')
        await page.get_by_test_id('spreadsheet-history-loading').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        assert await page.get_by_test_id('spreadsheet-history-loading').get_attribute('role') == 'status'
        assert await page.get_by_test_id('spreadsheet-name').is_visible()
        assert await page.get_by_test_id('spreadsheet-upload').is_enabled()
        assert await page.get_by_test_id('page-loading').count() == 0
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140016_6e7c1b2c157a/iteration4-spreadsheet-loading-desktop.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS: delayed history has role=status local loader; page available')
        hold.set()
        await page.get_by_test_id('spreadsheet-history-loading').wait_for(state='detached',timeout=15000)
        for i,item in enumerate(history):
            assert item['filename'] in await page.get_by_test_id('import-history-' + str(i)).inner_text()
        print('PASS: existing spreadsheet history displayed after delay')
        await page.unroute('**/api/spreadsheet/history',delayed_history)
        fail_history = True
        history_calls = []
        async def history_handler(route):
            history_calls.append(route.request.url)
            if fail_history:
                await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY history unavailable'}))
            else:
                await route.continue_()
        await page.route('**/api/spreadsheet/history',history_handler)
        await page.reload(wait_until='domcontentloaded')
        await page.get_by_test_id('spreadsheet-history-error').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(600)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.get_by_test_id('spreadsheet-history-retry').scroll_into_view_if_needed()
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_140016_6e7c1b2c157a/iteration4-spreadsheet-error-mobile.jpeg', type="jpeg", quality=40, full_page=False)
        fail_history = False
        before = len(history_calls)
        await page.get_by_test_id('spreadsheet-history-retry').click(force=True)
        await page.get_by_test_id('spreadsheet-history-error').wait_for(state='detached',timeout=15000)
        if history:
            await page.get_by_test_id('import-history-0').wait_for(timeout=15000)
            assert history[0]['filename'] in await page.get_by_test_id('import-history-0').inner_text()
        assert len(history_calls) > before
        assert not mutations
        print('PASS: spreadsheet503 retry reloads real history; zero write requests; mobile no overflow')
        await page.unroute('**/api/spreadsheet/history',history_handler)
        error_text = await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL spreadsheet scenario: ' + str(e))
        raise
