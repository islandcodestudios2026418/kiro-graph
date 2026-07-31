import sqlite3
import sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('graph.db')
c = conn.cursor()
now = datetime.now().isoformat()

# 完整系統架構
system_overview = '''tw-accounting 發票自動化系統架構：

【啟動流程】
開機 → tw-accounting-loop.ps1 → 監控雲端資料夾 → 發現新發票 → AI辨識 → 寫入Excel → 移動照片 → 刪除雲端原檔

【公司設定】
- 相磊：應收、應付、總帳（一般公司）
- 圓圓乙：應收、應付、總帳（一般公司）
- 展典投資：只有應付（外幣公司，需匯率轉換）

【資料夾】
雲端監控：H:\\我的雲端硬碟\\{公司}_{類型}
Excel輸出：C:\\Users\\user\\Desktop\\發票處理\\{公司}_{類型}
已處理照片：C:\\Users\\user\\Desktop\\發票處理\\已處理照片

【關鍵檔案】
- 程式碼：C:\\Users\\user\\tw-accounting\\
- 規則記憶：C:\\Users\\user\\kiro-graph\\graph.db
- 開機自動執行：Startup\\tw-accounting-auto.lnk'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-system-overview', 'skill', '系統架構總覽', 'tw-accounting', 'bookkeeper', system_overview, now, now))

# 應收帳款規則
receivable_rules = '''應收帳款 Excel 格式規則 (excel_output.py)：

【欄位順序】A~R 共18欄
項次、報價日期、請款日期、發票日期、發票號碼、客戶名稱、部門名稱、摘要、未收/未請、未稅金額、含稅金額、收款日期、金額、支票日期、金額、兌票日期、金額、備註

【特殊邊框】
- K/L欄之間：雙黑線分隔（含稅金額和收款日期之間）
- 最後資料列底部：粗黑線

【底部統計】
請款小計、請款合計、已收帳款、已收款合計、未兌現票據、已兌現票據、未收款合計、未請款合計

【排序】依發票日期排序'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-receivable-format', 'skill', '應收帳款格式規則', 'tw-accounting', 'bookkeeper', receivable_rules, now, now))

# 應付帳款規則
payable_rules = '''應付帳款 Excel 格式規則 (payable_output.py)：

【欄位順序】A~K 共11欄
項次、應付類型、日期、憑證類型、部門名稱、廠商統編、摘要、稅金、未稅額、應付金額、備註

【J欄標題】「應付金額」（不是含稅額）

【合計列】
- 米黃底色 (FFFDD0)
- 緊接資料列（不空行）
- 項次延續資料列

【排序規則】
先依應付類型分組，組內依日期排序
應付類型順序：帳款 → 楊蓁蓁 → 郭志葦 → 費用 → 薪資 → 獎金 → 零用金

【憑證類型】補、收據G、收據事務所、收據銀行、購票證明、繳費單、繳費證明、其他

【稅金計算】
- 收據類/薪資/獎金/零用金：不含營業稅，稅金留空
- 其他：稅金 = 未稅額 × 5%'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-payable-format', 'skill', '應付帳款格式規則', 'tw-accounting', 'bookkeeper', payable_rules, now, now))

# 總帳規則
ledger_rules = '''總帳 Excel 格式規則 (general_ledger.py)：

【費用科目】計入淨利
水電費、電話費、郵電費、文具用品、什項購置、稅捐、保險費、伙食費、油料費、修繕費、廣告費、交際費、旅費、運費、勞務費

【額外科目】不計入淨利，列在淨利下方，不加紅字標題
代付款、代收款、運輸設備、辦公設備、股東往來、台金借款、聯邦車貸

【月結算】
- 營業收入（應收帳款加總）
- 費用明細
- 淨利 = 營業收入 - 費用合計
- 額外科目（不影響淨利）'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-ledger-format', 'skill', '總帳格式規則', 'tw-accounting', 'bookkeeper', ledger_rules, now, now))

# 展典外幣規則
foreign_rules = '''展典投資外幣處理規則 (currency.py)：

【公司特性】
- 只有應付帳款（沒有應收、沒有總帳）
- 發票為外幣（USD、JPY、EUR等）

【處理流程】
1. AI辨識發票幣別和金額
2. 查詢當日匯率（台灣銀行）
3. 轉換成台幣金額
4. 記錄：原幣金額、幣別、匯率、台幣金額

【支援幣別】
USD（美元）、JPY（日圓）、EUR（歐元）、CNY（人民幣）、HKD（港幣）、GBP（英鎊）'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-foreign-currency', 'skill', '外幣處理規則', 'tw-accounting', 'bookkeeper', foreign_rules, now, now))

# 照片處理規則
photo_rules = '''發票照片處理規則：

【來源】Google Drive 雲端資料夾
H:\\我的雲端硬碟\\{公司}_{類型}

【支援格式】jpg、jpeg、png、heic、pdf

【處理後】
1. 複製到桌面「已處理照片」資料夾
2. 檔名加上日期戳記：原檔名_YYYYMMDD_HHMMSS.ext
3. 刪除雲端原檔（Google Drive 只做傳輸用，不儲存）

【去重機制】
- 用 SHA256 hash 判斷是否處理過
- 避免重複處理同一張發票'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-photo-handling', 'skill', '照片處理規則', 'tw-accounting', 'bookkeeper', photo_rules, now, now))

# 監控資料夾清單
folders_config = '''監控資料夾設定 (tw-accounting-loop.ps1)：

【雲端資料夾】7個
1. H:\\我的雲端硬碟\\相磊_應收 (receivable)
2. H:\\我的雲端硬碟\\相磊_應付 (payable)
3. H:\\我的雲端硬碟\\相磊_總帳 (ledger)
4. H:\\我的雲端硬碟\\圓圓乙_應收 (receivable)
5. H:\\我的雲端硬碟\\圓圓乙_應付 (payable)
6. H:\\我的雲端硬碟\\圓圓乙_總帳 (ledger)
7. H:\\我的雲端硬碟\\展典_應付 (payable, foreign)

【桌面輸出資料夾】
C:\\Users\\user\\Desktop\\發票處理\\{對應資料夾}
C:\\Users\\user\\Desktop\\發票處理\\已處理照片'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-folder-config', 'skill', '資料夾設定', 'tw-accounting', 'bookkeeper', folders_config, now, now))

conn.commit()

# 確認更新結果
c.execute("SELECT id, name FROM entities WHERE project='tw-accounting' ORDER BY id")
rows = c.fetchall()
print(f'kiro-graph 已更新！共 {len(rows)} 個規則：')
for row in rows:
    print(f'  - {row[0]}: {row[1]}')

conn.close()
