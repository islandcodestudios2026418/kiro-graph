import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime

db = sqlite3.connect('graph.db')
now = datetime.now().isoformat()

skills = [
    # 1. 總帳生成規則 (consolidate.py)
    {
        'id': 'skill-consolidate',
        'name': '總帳生成規則 (consolidate.py)',
        'body': """## 總帳生成規則

### 資料來源
從三個 Excel 彙整到總帳：
1. 應收帳款
2. 相磊應付帳款
3. 圓圓乙應付帳款

### 應付類型 → 總帳科目映射
```
帳款 → 廣告成本
車貸 → 營業費用
薪資 → 薪資
郭志葦 → 廣告成本
楊蓁蓁 → 廣告成本
零用金 → 雜費
費用 → 營業費用
```

### 排序規則
依扣款日期排序（民國年格式）

### 程式碼
```python
from consolidate import consolidate
consolidate()  # 讀取三個 Excel → 合併 → 依日期排序 → 寫入總帳
```""",
        'category': 'api-integration'
    },
    
    # 2. 部門代碼對照表
    {
        'id': 'skill-departments',
        'name': '部門代碼對照表',
        'body': """## 部門代碼對照表 (departments.json)

### 格式
代碼 → 部門名稱

### 代碼規則
- X 開頭
- 第2-3碼: 地區代號 (ZL=中壢, CP=青埔, GS=林口, GY=觀音...)
- 第4-6碼: 序號

### 主要部門
- XZL001~015: 中壢 (益展有福、華疆、月桃路...)
- XCP001~004: 青埔 (宜誠、樺龍、大華四期...)
- XGS001~002: 林口
- XGY001~004: 觀音/草漯
- XL001~007: 管理部門 (管理部、業務部、財務部、倉庫...)
- XLT001: 龍潭
- XLZ001: 南崁
- XML001: 苗栗
- XPD001~002: 八德

### 查詢函數
```python
from excel_output import lookup_dept  # 或 payable_output, general_ledger
dept_name = lookup_dept("XZL001")  # → "中壢益展有福接待"
```""",
        'category': 'config'
    },
    
    # 3. 廠商/客戶對照表
    {
        'id': 'skill-vendor-customer',
        'name': '廠商/客戶對照表',
        'body': """## 廠商與客戶對照表

### 廠商對照表 (vendors.json) — 應付帳款用
格式: 統編(8位) → 廠商簡稱(2-4字)
用途: AI 辨識到統編後，自動查表填入廠商簡稱到摘要欄位

```python
from payable_output import lookup_vendor
vendor = lookup_vendor("12345678")  # → "台積電"
```

### 客戶對照表 (customers.json) — 應收帳款用
格式: 統編(8位) → 客戶名稱
用途: AI 辨識到統編後，自動查表填入客戶名稱

```python
from excel_output import lookup_customer
customer = lookup_customer("12345678")  # → "大華建設"
```

### 新增對照資料
直接編輯 JSON 檔案：
- src/vendors.json
- src/customers.json""",
        'category': 'config'
    },
    
    # 4. 下拉選單選項
    {
        'id': 'skill-dropdown-options',
        'name': '下拉選單選項',
        'body': """## Excel 下拉選單選項

### 應付帳款 (payable_output.py)

**B欄 - 應付類型** (7項，固定順序):
1. 帳款
2. 楊蓁蓁
3. 郭志葦
4. 費用
5. 薪資
6. 獎金
7. 零用金

**D欄 - 憑證類型** (8項):
1. 補
2. 收據G
3. 收據事務所
4. 收據銀行
5. 購票證明
6. 繳費單
7. 繳費證明
8. 其他

### 應收帳款 (excel_output.py)

**I欄 - 未收/未請** (2項):
1. 未收
2. 未請

### 總帳 (general_ledger.py)

**B欄 - 科目** (依公司不同):

相磊(工程): 工程收入1, 工程收入, 其他收入1, 其他收入, 工程成本-材料, 工程成本-工料, 工程成本-工資, 工程成本-費用, 薪資, 勞務費, 營業稅, 營所稅...

圓圓乙(廣告): 廣告收入1, 廣告收入, 其他收入1, 其他收入, 廣告成本-廣告費, 廣告成本-影音費, 廣告成本-稿費...""",
        'category': 'config'
    },
    
    # 5. 條件式格式
    {
        'id': 'skill-conditional-format',
        'name': 'Excel 條件式格式',
        'body': """## Excel 條件式格式

### 應收帳款
- **I欄 = "未收"** → 整行粉紅色背景 (FFD9D9)
- 用途: 一眼看出哪些款項還沒收到

### 程式碼位置
excel_output.py → init_excel():
```python
ws.conditional_formatting.add(
    "A4:R999",
    FormulaRule(formula=['$I4="未收"'], fill=PINK_FILL)
)
```""",
        'category': 'config'
    },
    
    # 6. 列印設定
    {
        'id': 'skill-print-settings',
        'name': 'Excel 列印設定',
        'body': """## Excel 列印設定

### 共通設定
- 方向: 直向 (Portrait)
- 紙張: A4
- 縮放: 寬度 1 頁 (fitToWidth=1)
- 高度: 自動 (fitToHeight=0)
- 標題列: 前3列每頁重複 (print_title_rows='1:3')

### 頁首
- 右側: 列印日期 &[Date]

### 頁尾
- 中間: 總經理:_______ 副總經理:_______ 財務:_______

### 凍結窗格
- 凍結在 A4 (標題列固定)""",
        'category': 'config'
    },
    
    # 7. 健康檢查
    {
        'id': 'skill-health-check',
        'name': '啟動健康檢查',
        'body': """## 啟動健康檢查 (health_check.py)

### 11 項檢查項目
1. Python 版本 >= 3.11
2. 必要套件已安裝
3. Google Drive 路徑存在
4. 4 個監控資料夾存在
5. credentials/ 資料夾存在
6. 憑證檔案已加密
7. 設定檔格式正確
8. 磁碟空間 > 100MB
9. 網路連線正常
10. 稽核日誌完整性 (hash chain)
11. Excel 檔案可寫入

### 呼叫方式
```python
from health_check import run_health_check
ok, errors = run_health_check()
if not ok:
    for e in errors:
        print(e)
```

### CLI
```bash
python src/server.py --health
```""",
        'category': 'config'
    },
]

for s in skills:
    db.execute('''INSERT OR REPLACE INTO entities 
        (id, type, name, project, agent, status, body, category, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (s['id'], 'skill', s['name'], 'tw-accounting', 'system', 'active',
         s['body'], s.get('category'), now, now))
    
    db.execute('INSERT OR IGNORE INTO edges (src, dst, rel, created) VALUES (?, ?, ?, ?)',
        ('tw-accounting', s['id'], 'owns', now))

db.commit()
print(f'已新增 {len(skills)} 個規則')

# 刪除測試資料
db.execute('DELETE FROM entities WHERE id=?', ('test-1',))
db.commit()

# 列出所有
print()
print('=== 目前所有 Skills ===')
for row in db.execute('SELECT id, name FROM entities WHERE type=? AND project=? ORDER BY id', ('skill', 'tw-accounting')):
    print(f'  {row[0]}: {row[1]}')

db.close()
