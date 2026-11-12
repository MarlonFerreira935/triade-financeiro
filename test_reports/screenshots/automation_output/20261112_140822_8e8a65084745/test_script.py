async def run_test(page, output_dir, page_url):
    import json
    from urllib.parse import urlsplit
    base=urlsplit(page.url).scheme+'://'+urlsplit(page.url).netloc
    writes=[]
    state={'fail':True,'calls':0}
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        await page.get_by_test_id('period-select').wait_for(timeout=20000)
        month=await page.get_by_test_id('period-select').input_value()
        baseline=await (await page.request.get(base+'/api/alerts?month='+month)).json()
        async def block_write(route):
            if route.request.method not in ['GET','HEAD','OPTIONS']:
                writes.append(route.request.url)
                await route.abort()
            else: await route.continue_()
        async def alerts(route):
            state['calls']+=1
            if state['fail']: await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_ONLY alert503'}))
            else: await route.continue_()
        await page.route('**/api/**',block_write)
        await page.route('**/api/alerts?*',alerts)
        await page.goto(base+'/alertas',wait_until='domcontentloaded')
        await page.get_by_test_id('alerts-load-error').wait_for(timeout=15000)
        assert await page.get_by_test_id('alerts-retry').is_visible()
        assert await page.get_by_test_id('page-loading').count()==0
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path=output_dir+'/iteration5-alerts-error-desktop.jpeg', type='jpeg', quality=40, full_page=False)
        state['fail']=False
        before=state['calls']
        await page.get_by_test_id('alerts-retry').click()
        await page.get_by_test_id('alert-total-count').wait_for(timeout=15000)
        assert state['calls']>before
        for testid,key in [('alert-total-count','count'),('alert-critical-count','critical_count'),('alert-unread-count','unread_count')]:
            assert (await page.get_by_test_id(testid).inner_text()).split()[0]==str(baseline[key])
        after=await (await page.request.get(base+'/api/alerts?month='+month)).json()
        assert [(x['id'],x['acknowledged']) for x in baseline['alerts']]==[(x['id'],x['acknowledged']) for x in after['alerts']]
        assert not writes
        print('PASS alerts503/retry; real count/critical/unread match; acknowledgment state unchanged; zero writes')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(350)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        await page.screenshot(path=output_dir+'/iteration5-alerts-mobile.jpeg', type='jpeg', quality=40, full_page=False)
        print('PASS alerts desktop/mobile no overflow')
        error_text=await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
    except Exception as e:
        print('FAIL alerts regression '+repr(e))
        raise
