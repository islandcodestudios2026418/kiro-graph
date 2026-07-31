import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('graph.db')
c = conn.cursor()
c.execute("SELECT id, name FROM entities WHERE project='tw-accounting' ORDER BY id")
for row in c.fetchall():
    print(f'{row[0]}: {row[1]}')
