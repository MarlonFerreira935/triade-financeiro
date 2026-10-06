import os
import requests

storage_key = None

def storage_url():
    return os.environ['INTEGRATION_PROXY_URL'].rstrip('/') + '/objstore/api/v1/storage'

def init_storage(force=False):
    global storage_key
    if storage_key and not force: return storage_key
    r=requests.post(f'{storage_url()}/init',json={'emergent_key':os.environ['EMERGENT_LLM_KEY']},timeout=30)
    r.raise_for_status();storage_key=r.json()['storage_key'];return storage_key

def put_object(path,data,mime):
    r=requests.put(f'{storage_url()}/objects/{path}',headers={'X-Storage-Key':init_storage(),'Content-Type':mime},data=data,timeout=90)
    r.raise_for_status();return r.json()

def get_object(path):
    r=requests.get(f'{storage_url()}/objects/{path}',headers={'X-Storage-Key':init_storage()},timeout=60)
    r.raise_for_status();return r.content