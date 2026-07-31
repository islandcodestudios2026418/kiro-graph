import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime

db = sqlite3.connect('graph.db')
now = datetime.now().isoformat()

body = """## 總帳自動化 (general_ledger.py)

### 兩份總帳
1. **相磊** (工程類)
2. **圓圓乙** (廣告類)

### Excel 欄位 (A~H)
1. 扣款日期
2. 科目 (下拉選單)
3. 部門
4. 統編
5. 摘要
6. 收入
7. 支出
8. 帳戶餘額 (使用者手動填)

### 相磊科目 (工程類)
**收入**: 工程收入1, 工程收入, 其他收入1, 其他收入
**成本**: 工程成本-材料, 工程成本-工料, 工程成本-工資, 工程成本-費用
**費用**: 薪資, 勞務費, 營業稅, 營所稅, 勞保費用, 健保費用, 勞退費用, 營業費用, 交通費, 其他費用
**其他**: 運輸設備, 辦公設備, 代付款, 代收款, 股東往來, 利息收入, 台金借款, 聯邦車貸

### 圓圓乙科目 (廣告類)
**收入**: 廣告收入1, 廣告收入, 其他收入1, 其他收入
**成本**: 廣告成本-廣告費, 廣告成本-影音費, 廣告成本-稿費, 廣告成本-薪資, 廣告成本-費用, 廣告成本
**費用**: 同上 (薪資, 勞務費, 營業稅 等)

### 每月統計小表
Excel 下方自動產生 SUMIF 公式統計:
- 各科目收入/支出金額
- 收入小計
- 支出小計
- 淨利 = 收入小計 - 支出小計

### 程式碼
```python
from general_ledger import init_general_ledger, add_entry

# 建立新檔案
init_general_ledger(path, company_key="相磊")

# 新增一筆
add_entry(path, {
    "扣款日期": "115/07/31",
    "科目": "工程收入",
    "部門": "中壢",
    "統編": "12345678",
    "摘要": "XXX工程款",
    "收入": 100000,
    "支出": None
}, company_key="相磊")
```

### Excel 路徑
- 相磊: EXCEL_PATHS["general_相磊"]
- 圓圓乙: EXCEL_PATHS["general_圓圓乙"]"""

db.execute('''INSERT OR REPLACE INTO entities 
    (id, type, name, project, agent, status, body, category, created, updated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
    ('skill-general-ledger', 'skill', '總帳自動化', 'tw-accounting', 'system', 'active',
     body, 'api-integration', now, now))

db.execute('INSERT OR IGNORE INTO edges (src, dst, rel, created) VALUES (?, ?, ?, ?)',
    ('tw-accounting', 'skill-general-ledger', 'owns', now))

db.commit()
print('已新增總帳自動化 skill')
db.close()
