import sqlite3
import json
from datetime import datetime

db = sqlite3.connect('graph.db')
db.executescript(open('schema.sql').read())

now = datetime.now().isoformat()

# 專案實體
entities = [
    # 專案本身
    {
        'id': 'tw-accounting',
        'type': 'project',
        'name': 'tw-accounting 發票自動化系統',
        'project': None,
        'agent': 'system',
        'status': 'active',
        'body': '''台灣會計發票自動辨識與 Excel 記帳系統。

## 目的
自動辨識發票照片，寫入應收/應付帳款 Excel。

## 核心流程
1. 監控雲端硬碟資料夾
2. 複製照片到桌面處理
3. 辨識發票內容
4. 寫入 Excel (存桌面)
5. 移動照片到「已處理」資料夾
6. 刪除雲端原檔''',
        'category': None
    },
    
    # 發票辨識
    {
        'id': 'skill-invoice-recognition',
        'type': 'skill',
        'name': '發票辨識規則',
        'project': 'tw-accounting',
        'agent': 'system',
        'status': 'active',
        'body': '''## 發票辨識要點

### 發票號碼格式
- 格式: XX-12345678 (兩個英文字母 + 8位數字)
- 範例: CU-02257150, DC-76142955

### 日期格式
- 民國年: 115/MM/DD
- 範例: 115/07/31

### 必須辨識欄位
1. 發票號碼 (必填)
2. 日期 (必填)
3. 含稅金額 (必填)
4. 統編 (8位數字)
5. 品名/摘要

### HEIC 轉換
如果是 .heic 檔案，先轉 jpg:
```python
from PIL import Image
import pillow_heif
pillow_heif.register_heif_opener()
img = Image.open('照片.heic')
img.save('temp.jpg', 'JPEG')
```''',
        'category': 'data-format'
    },
    
    # Excel 寫入
    {
        'id': 'skill-excel-write',
        'type': 'skill',
        'name': 'Excel 寫入方式',
        'project': 'tw-accounting',
        'agent': 'system',
        'status': 'active',
        'body': '''## Excel 寫入

### 呼叫方式
```python
import sys
sys.path.insert(0, 'C:/Users/user/tw-accounting/src')
from pipeline import process_with_data

result = process_with_data(
    {
        '發票': 'XX-12345678',
        '發票日期': '115/07/31',
        '含稅金額': 1000,
        '統編': '12345678',
        '品名': '商品名稱'
    },
    'receivable',  # 或 'payable'
    '圓圓乙',      # 或 '相磊'
    'IMG_9969.HEIC'
)
```

### 參數說明
- folder_type: 'receivable' (應收) 或 'payable' (應付)
- company: '相磊' 或 '圓圓乙'

### Excel 輸出位置
C:/Users/user/Desktop/發票處理/
├── 相磊_應收/相磊_應收帳款.xlsx
├── 相磊_應付/相磊_應付帳款.xlsx  
├── 圓圓乙_應收/圓圓乙_應收帳款.xlsx
├── 圓圓乙_應付/圓圓乙_應付帳款.xlsx
└── 已處理照片/''',
        'category': 'api-integration'
    },
    
    # 雲端監控
    {
        'id': 'skill-cloud-watch',
        'type': 'skill',
        'name': '雲端資料夾監控',
        'project': 'tw-accounting',
        'agent': 'system',
        'status': 'active',
        'body': '''## 雲端資料夾結構

### 監控路徑
H:/我的雲端硬碟/
├── 相磊_應收/     → receivable, 相磊
├── 相磊_應付/     → payable, 相磊
├── 圓圓乙_應收/   → receivable, 圓圓乙
└── 圓圓乙_應付/   → payable, 圓圓乙

### 處理流程
1. 掃描雲端資料夾找 .heic/.jpg/.png/.pdf
2. 複製到桌面對應資料夾
3. 辨識處理
4. 成功後刪除雲端原檔

### 掃描程式
```python
from pipeline import scan_cloud_folders
pending = scan_cloud_folders()
# 回傳: [(cloud_path, folder_type, company), ...]
```''',
        'category': 'config'
    },
    
    # 去重
    {
        'id': 'skill-dedup',
        'type': 'skill',
        'name': '發票去重機制',
        'project': 'tw-accounting',
        'agent': 'system',
        'status': 'active',
        'body': '''## 發票去重

### 原理
用發票號碼檢查是否已處理過。

### 檢查方式
```python
from dedup import is_duplicate
if is_duplicate('CU-02257150'):
    print('此發票已存在')
```

### 快取機制
- 寫入 Excel 後自動呼叫 invalidate_cache()
- 快取 30 秒內有效，避免重複讀取

### Ledger 位置
- src/ledger.json (應收)
- src/ledger_payable.json (應付)''',
        'category': 'logic-bug'
    },
    
    # 工作循環
    {
        'id': 'skill-work-loop',
        'type': 'skill',
        'name': '工作循環模式',
        'project': 'tw-accounting',
        'agent': 'system',
        'status': 'active',
        'body': '''## 自動工作循環

### 啟動後行為
1. 檢查 pending-invoices/ 有沒有 .json 任務
2. 處理所有任務
3. 等待 60 秒
4. 回到步驟 1

### 任務 JSON 格式
```json
{
    "path": "H:/我的雲端硬碟/圓圓乙_應收/IMG_9969.HEIC",
    "type": "receivable",
    "company": "圓圓乙",
    "name": "IMG_9969.HEIC"
}
```

### 重要規則
- 永遠不要停下來等使用者
- 遇到錯誤記錄後跳過，繼續下一個
- 這是全自動系統''',
        'category': 'loop-control'
    },
]

for e in entities:
    db.execute('''INSERT OR REPLACE INTO entities 
        (id, type, name, project, agent, status, body, evidence, category, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (e['id'], e['type'], e['name'], e.get('project'), e['agent'], e['status'], 
         e['body'], None, e.get('category'), now, now))

# 建立關係
edges = [
    ('tw-accounting', 'skill-invoice-recognition', 'owns'),
    ('tw-accounting', 'skill-excel-write', 'owns'),
    ('tw-accounting', 'skill-cloud-watch', 'owns'),
    ('tw-accounting', 'skill-dedup', 'owns'),
    ('tw-accounting', 'skill-work-loop', 'owns'),
    ('skill-excel-write', 'skill-dedup', 'depends_on'),
    ('skill-cloud-watch', 'skill-invoice-recognition', 'depends_on'),
]

for src, dst, rel in edges:
    db.execute('INSERT INTO edges (src, dst, rel, created) VALUES (?, ?, ?, ?)',
        (src, dst, rel, now))

db.commit()
print(f'已寫入 {len(entities)} 個實體和 {len(edges)} 個關係到 graph.db')
db.close()
