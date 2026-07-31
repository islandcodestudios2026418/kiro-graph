import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('graph.db')
c = conn.cursor()
c.execute("SELECT id, name, body FROM entities WHERE type='tension' ORDER BY updated DESC LIMIT 5")
rows = c.fetchall()
if rows:
    for row in rows:
        print(f'ID: {row[0]}')
        print(f'Name: {row[1]}')
        print(f'Body: {row[2][:200] if row[2] else "(empty)"}...')
        print('---')
else:
    print('沒有找到 tension (錯誤記錄)')
