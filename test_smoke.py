"""Quick smoke test for kiro-graph."""
import sys
sys.path.insert(0, '.')
from server import init_db, get_db
init_db()
db = get_db()
tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"OK, tables: {tables}")
# Test insert
from server import now
import uuid, json
eid = str(uuid.uuid4())[:8]
ts = now()
db.execute("INSERT INTO entities (id,type,name,project,agent,status,body,evidence,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?)",
           (eid, "project", "test-project", None, "main", "active", "test body", "[]", ts, ts))
db.commit()
row = db.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
print(f"Entity created: {dict(row)}")
# FTS test
fts = db.execute("SELECT name FROM entities_fts WHERE entities_fts MATCH 'test'").fetchall()
print(f"FTS search 'test': {[r[0] for r in fts]}")
# Cleanup
db.execute("DELETE FROM entities WHERE id=?", (eid,))
db.commit()
print("All tests passed!")
