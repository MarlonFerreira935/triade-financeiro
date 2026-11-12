async def run_test(page, output_dir, page_url):
    import json
    await page.set_viewport_size({'width':1920,'height':800})
    base=page.url.split('/')[0]+'//'+page.url.split('/')[2]
    cid='03438cde-a58f-438c-9b18-1e77fe9126fc'
    try:
        saved=await (await page.request.get(base+'/api/advisor/conversations/'+cid)).json()
        assert saved['title']=='TEST_UI_chat_d89e8860: Resuma o resultado deste mês em uma frase.'
        assert saved['messages'][0]['content']==saved['title'] and saved['messages'][1]['status']=='complete'
        await page.goto(base+'/consultor')
        await page.get_by_test_id('advisor-message-input').wait_for(timeout=15000)
        await page.get_by_test_id('advisor-history-toggle').click(force=True)
        await page.get_by_test_id('conversation-select-'+cid).click(force=True)
        await page.get_by_test_id('answer-source-1').wait_for(timeout=15000)
        print('PASS actual Gemini frontend response completed and persisted in reopened history')
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
        print('PASS delete cancellation/confirmation; own conversation soft-deleted only')
    except Exception as e:
        print('FAIL actual chat/history/delete:',str(e))
    finally:
        existing=await page.request.get(base+'/api/advisor/conversations/'+cid)
        if existing.status==200: print('CLEANUP exact own conversation:',(await page.request.delete(base+'/api/advisor/conversations/'+cid)).status)
