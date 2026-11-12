async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width":1920,"height":800})
        await page.get_by_test_id('chart-monthly').wait_for(timeout=20000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path='/app/test_reports/screenshots/automation_output/20261112_134721_8f4df9fd3598/t1-overview.jpeg', type="jpeg", quality=40, full_page=False)
        print('PASS frontend loads and charts rendered')
        print(await page.locator('[data-testid]').evaluate_all('(els)=>els.map(e=>e.dataset.testid)'))
    except Exception as e:
        print('FAIL initial load:',str(e))
