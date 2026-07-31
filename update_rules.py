import sqlite3
import sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('graph.db')
c = conn.cursor()

now = datetime.now().isoformat()

# 更新應收帳款格式規則
receivable_rules = '''應收帳款 Excel 格式規則：
- K欄和L欄之間：雙黑線分隔（含稅金額和收款日期之間）
- 最後資料列底部：粗黑線
- 新發票進來時，底部統計區自動往下挪
- 欄位順序：項次、報價日期、請款日期、發票日期、發票號碼、客戶名稱、部門名稱、摘要、未收/未請、未稅金額、含稅金額、收款日期、金額、支票日期、金額、兌票日期、金額、備註'''

c.execute('UPDATE entities SET body = ?, updated = ? WHERE id = ?', 
          (receivable_rules, now, 'skill-excel-write'))
print(f'更新 skill-excel-write: {c.rowcount} rows')

# 新增應付帳款格式規則
payable_rules = '''應付帳款 Excel 格式規則：
- B欄：應付類型、C欄：日期
- J欄標題：「應付金額」（不是含稅額）
- 合計列：米黃底色 (FFFDD0)
- 合計列緊接資料列（不空行）
- 合計列項次延續資料列
- 排序：先依應付類型分組，組內依日期排序
- 應付類型順序：帳款、楊蓁蓁、郭志葦、費用、薪資、獎金、零用金'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-payable-format', 'skill', '應付帳款格式規則', 'tw-accounting', 'bookkeeper', payable_rules, now, now))
print(f'新增 skill-payable-format')

# 更新總帳規則
ledger_rules = '''總帳 Excel 格式規則：
- 費用科目計入淨利：水電費、電話費、郵電費、文具用品、什項購置、稅捐、保險費、伙食費、油料費、修繕費、廣告費、交際費、旅費、運費、勞務費
- 額外科目（不計入淨利，列在淨利下方）：代付款、代收款、運輸設備、辦公設備、股東往來、台金借款、聯邦車貸
- 額外科目不加紅字標題，直接列出'''

c.execute('UPDATE entities SET body = ?, updated = ? WHERE id = ?', 
          (ledger_rules, now, 'skill-general-ledger'))
print(f'更新 skill-general-ledger: {c.rowcount} rows')

conn.commit()
conn.close()
print('kiro-graph 規則已更新完成！')
