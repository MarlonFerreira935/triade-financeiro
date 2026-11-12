"""Read-only database guard and exact TEST_ conversation soft-delete verification."""
import hashlib
import json
import sys
from pathlib import Path

from bson import json_util
from dotenv import dotenv_values
from pymongo import MongoClient

config = dotenv_values('/app/backend/.env')
db = MongoClient(config['MONGO_URL'])[config['DB_NAME']]
path = Path('/app/test_reports/iteration4-db-baseline.json')

def snapshot():
    return {name: {str(doc['_id']): hashlib.sha256(json_util.dumps(doc, sort_keys=True).encode()).hexdigest()
                   for doc in db[name].find({})} for name in db.list_collection_names()}

if sys.argv[1] == 'before':
    path.write_text(json.dumps(snapshot()))
    print('Read-only baseline saved; no database writes.')
else:
    before = json.loads(path.read_text())
    after = snapshot()
    changes = [(name, key) for name, docs in before.items() for key, digest in docs.items()
               if after.get(name, {}).get(key) != digest]
    assert not changes, f'Original records changed: {changes}'
    print('PASS: all original records unchanged in every collection.')
    if len(sys.argv) > 2:
        cid = sys.argv[2]
        record = db.conversations.find_one({'id': cid})
        assert record and record['title'].startswith('TEST_') and record['is_deleted'] is True
        messages = list(db.advisor_messages.find({'conversation_id': cid}))
        assert len(messages) == 2
        assert next(m for m in messages if m['role'] == 'user')['content'].startswith('TEST_')
        assert next(m for m in messages if m['role'] == 'assistant')['status'] == 'complete'
        print(f'PASS: own conversation {cid} is_deleted=true; both messages preserved.')