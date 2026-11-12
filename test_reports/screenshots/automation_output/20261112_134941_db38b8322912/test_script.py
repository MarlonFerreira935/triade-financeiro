async def run_test(page, output_dir, page_url):
    import asyncio, json
    from urllib.parse import urlparse, parse_qs
    results=[]
    await page.set_viewport_size({'width':1920,'height':800})
    base=page.url.split('/')[0]+'//'+page.url.split('/')[2]
    for route_name,endpoint,retry_id in [('lancamentos','transactions','transactions-retry'),('comprovantes','receipts','receipts-retry'),('dre','dre','dre-retry'),('planilhas','spreadsheet/history','spreadsheet-history-retry')]:
        pattern='**/api/'+endpoint+'*'
        async def fail(route):
            await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST_only_failure'}))
        try:
            await page.route(pattern,fail)
            await page.goto(base+'/'+route_name)
            await page.get_by_test_id(retry_id).wait_for(timeout=15000)
            await page.unroute(pattern,fail)
            await page.get_by_test_id(retry_id).click(force=True)
            await page.get_by_test_id(retry_id).wait_for(state='hidden',timeout=15000)
            results.append({'test':endpoint+' error/retry','passed':True})
            print('PASS',endpoint,'error/retry')
        except Exception as e:
            results.append({'test':endpoint+' error/retry','passed':False,'error':str(e)})
            print('FAIL',endpoint,str(e))
            await page.unroute(pattern,fail)
    for endpoint,route_name in [('transactions','lancamentos'),('receipts','comprovantes')]:
        pattern='**/api/'+endpoint+'*'
        seen=[]
        async def delay_period(route):
            month=parse_qs(urlparse(route.request.url).query).get('month',[''])[0]
            seen.append(month)
            if month=='2026-07': await asyncio.sleep(1.8)
            if endpoint=='transactions':
                item={'id':'TEST_'+month,'description':'TEST_period_'+month,'date':month+'-01','amount':1,'account_id':'50','category':'Administrativo e TI','type':'despesa','source':'manual','status':'confirmado','created_at':'2026-01-01T00:00:00Z'}
            else:
                item={'id':'TEST_'+month,'filename':'TEST_period_'+month+'.pdf','date':month+'-01','amount':None,'category':'Administrativo e TI','content_type':'application/pdf','status':'pendente','extraction':{}}
            try: await route.fulfill(status=200,content_type='application/json',body=json.dumps([item]))
            except Exception: pass
        try:
            await page.route(pattern,delay_period)
            await page.goto(base+'/'+route_name)
            await page.get_by_test_id('period-select').wait_for(timeout=15000)
            await page.get_by_test_id('period-select').select_option('2026-07')
            await page.get_by_test_id('period-select').wait_for(timeout=15000)
            await page.wait_for_timeout(150)
            await page.get_by_test_id('period-select').select_option('2026-08')
            await page.get_by_text('TEST_period_2026-08',exact=False).first.wait_for(timeout=15000)
            await page.wait_for_timeout(2200)
            assert await page.get_by_text('TEST_period_2026-07',exact=False).count()==0
            assert '2026-07' in seen and '2026-08' in seen
            results.append({'test':endpoint+' old response ignored','passed':True})
            print('PASS',endpoint,'old response ignored',seen)
        except Exception as e:
            results.append({'test':endpoint+' old response ignored','passed':False,'error':str(e)})
            print('FAIL',endpoint,'stale response',str(e))
        finally:
            await page.unroute(pattern,delay_period)
    try:
        async def fail_alerts(route): await route.fulfill(status=503,content_type='application/json',body='{"detail":"TEST_alert_failure"}')
        await page.route('**/api/alerts?*',fail_alerts)
        await page.goto(base+'/alertas')
        await page.get_by_test_id('period-select').wait_for(timeout=15000)
        await page.wait_for_timeout(2200)
        loading=await page.get_by_test_id('page-loading').count()
        retry=await page.locator('[data-testid*="retry"]').count()
        print('OBSERVED alerts failure: loading=',loading,'retry=',retry)
        results.append({'test':'alerts error recovery','passed':not loading,'loading':loading,'retry':retry})
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_134941_db38b8322912/t1-alerts-error.jpeg', type="jpeg", quality=40, full_page=False)
    except Exception as e: print('FAIL alerts error check',str(e))
    finally: await page.unroute('**/api/alerts?*',fail_alerts)
    error_text=await page.evaluate('''() => {const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', ');}''')
    print('Found error message: '+error_text if error_text else 'No error messages found on the page')
    print('UI_RESULTS',json.dumps(results))
