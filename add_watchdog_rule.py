import sqlite3
from datetime import datetime

conn = sqlite3.connect('graph.db')
c = conn.cursor()
now = datetime.now().isoformat()

rule = '''監督者 (Watchdog) 機制：

【用途】
監督 tw-accounting agent，防止卡住、自動修復問題

【功能】
1. 預先壓縮大圖片（>4.5MB）避免 API 錯誤
2. 監控 agent 是否存活，卡住時自動重啟
3. 記錄所有問題到 kiro-graph

【運作方式】
- 每 30 秒掃描一次監控資料夾
- 發現大圖片 → 自動壓縮 → 記錄到 graph
- 發現 agent 停止 → 自動重啟 → 記錄到 graph

【啟動方式】
使用 tw-accounting-start.ps1 同時啟動 Agent 和監督者

【程式碼位置】
- watchdog.py：監督者主程式
- tw-accounting-start.ps1：啟動腳本

【記錄格式】
- type: tension
- agent: watchdog
- status: done (已處理)'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-watchdog', 'skill', '監督者機制', 'tw-accounting', 'watchdog', rule, now, now))

conn.commit()
print('已新增 skill-watchdog')
