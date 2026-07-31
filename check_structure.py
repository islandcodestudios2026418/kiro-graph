import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('graph.db')
c = conn.cursor()

# 查看 entities 結構
c.execute("PRAGMA table_info(entities)")
print("entities columns:", c.fetchall())

# 查看現有 entities
c.execute("SELECT id, name FROM entities LIMIT 5")
print("sample entities:", c.fetchall())
