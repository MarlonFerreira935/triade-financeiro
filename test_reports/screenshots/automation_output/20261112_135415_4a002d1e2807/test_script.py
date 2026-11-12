async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({'width':1920,'height':800})
        base=page.url.split('/')[0]+'//'+page.url.split('/')[2]
        meta=await (await page.request.get(base+'/api/meta')).json()
        records=await (await page.request.get(base+'/api/advisor/conversations?month='+meta['default_month'])).json()
        print('TEST chat identities for exact cleanup:', [{'id':c['id'],'title':c['title'],'created_at':c['created_at']} for c in records if c['title'].startswith('TEST_UI_chat_')])
    except Exception as e: print('FAIL identifying own chat',str(e))
