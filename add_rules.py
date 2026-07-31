import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime

db = sqlite3.connect('graph.db')
now = datetime.now().isoformat()

skills = [
    # 排序規則
    {
        'id': 'skill-sort-rules',
        'name': 'Excel 排序規則',
        'body': '''## Excel 排序規則

### 應收帳款 (excel_output.py)
依「報價日期」排序（民國年格式，如 115/07/31）
- 日期越早排越前面
- 相同日期維持輸入順序

### 應付帳款 (payable_output.py)
**兩層排序**：

1. **第一層：應付類型分組** (固定順序)
   1. 帳款
   2. 楊蓁蓁
   3. 郭志葦
   4. 費用
   5. 薪資
   6. 獎金
   7. 零用金

2. **第二層：同類型內依日期排序**
   - 日期越早排越前面

### 項次編號規則
應付帳款的項次格式: YYMMNN
- YY: 民國年 (如 115)
- MM: 月份 (01-12)
- NN: 該月序號 (01-99)
- 範例: 1150701 = 115年7月第1筆

### 程式碼位置
- src/excel_output.py → _sort_by_date()
- src/payable_output.py → _sort_by_type_and_date(), PAYABLE_TYPES''',
        'category': 'config'
    },
    
    # 發票辨識規則
    {
        'id': 'skill-invoice-rules',
        'name': '發票處理規則 (invoice-worker)',
        'body': '''## 發票處理規則

### 必須提取的欄位
1. 發票號碼 (XX-12345678)
2. 日期 (民國年 115/MM/DD)
3. 統編 (8位數字)
4. 品名
5. 金額、稅額
6. B2B/B2C 類型

### 分類
- 進項 (purchase) vs 銷項 (sales)
- 公帳 vs 私帳

### 驗證規則
- 統編 check digit 驗證
- 稅額 = 金額 × 5% (一致性檢查)
- 重複發票偵測

### 安全規則
- 禁止記錄明文財務資料，只用 record ID
- 低信心度 OCR 欄位標記為需人工審核
- 每張發票都有唯一內部 ID + hash 供稽核''',
        'category': 'data-format'
    },
    
    # 記帳規則
    {
        'id': 'skill-bookkeeping-rules',
        'name': '記帳規則 (bookkeeper-worker)',
        'body': '''## 記帳規則

### 會計原則
- 權責發生制 (Accrual basis) — 公司必須使用
- 複式簿記: 每筆借方都有對等的貸方

### 稅額處理
- 進項稅額 → 留抵稅額 or 應付營業稅
- 銷項稅額 → 應付營業稅

### 帳本分離
- 公帳和私帳完全分開
- 禁止混合公帳私帳分錄
- 股東往來需要在兩邊都記錄

### 審核流程
提交到 review-queue/pending/bookkeeping-{date}-{id}.json''',
        'category': 'logic-bug'
    },
    
    # 稅務規則
    {
        'id': 'skill-tax-rules',
        'name': '稅務申報規則 (tax-worker)',
        'body': '''## 稅務申報規則

### 稅務類型
1. **營業稅** (雙月): 銷項稅額 − 進項稅額 = 應納稅額, 401表
2. **扣繳** (月): 薪資、租金、顧問費的扣繳
3. **營所稅** (年): (收入 − 成本 − 費用) = 課稅所得 × 20%
4. **未分配盈餘稅**: 未分配盈餘 × 5%

### 稅務行事曆
- 1/15: 11-12月營業稅
- 1/31: 扣繳年報
- 3/15: 1-2月營業稅
- 5/15: 3-4月營業稅
- 5/31: 營所稅
- 7/15: 5-6月營業稅
- 9/15: 7-8月營業稅
- 9/30: 暫繳
- 11/15: 9-10月營業稅

### 核對
發票 ↔ 分錄 ↔ 稅表 必須一致''',
        'category': 'config'
    },
]

for s in skills:
    db.execute('''INSERT OR REPLACE INTO entities 
        (id, type, name, project, agent, status, body, category, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (s['id'], 'skill', s['name'], 'tw-accounting', 'system', 'active',
         s['body'], s.get('category'), now, now))
    
    # 建立關係
    db.execute('INSERT OR IGNORE INTO edges (src, dst, rel, created) VALUES (?, ?, ?, ?)',
        ('tw-accounting', s['id'], 'owns', now))

db.commit()
print(f'已新增 {len(skills)} 個規則到 kiro-graph')

# 列出所有 skills
print()
print('=== 目前所有 Skills ===')
for row in db.execute('SELECT id, name FROM entities WHERE type=? AND project=?', ('skill', 'tw-accounting')):
    print(f'  {row[0]}: {row[1]}')

db.close()
