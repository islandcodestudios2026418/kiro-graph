import sqlite3
from datetime import datetime

conn = sqlite3.connect('graph.db')
c = conn.cursor()
now = datetime.now().isoformat()

rule = '''圖片大小限制規則：

【問題】
Bedrock API 限制圖片最大 5MB，超過會報錯：
"image exceeds 5 MB maximum"

【解決方案】
在辨識前自動壓縮圖片到 4.5MB 以下（留餘量）

【壓縮策略】
1. 先降低 JPEG 品質：85 → 75 → 65 → 55 → 45
2. 如果還是太大，縮小尺寸：80% → 60% → 50% → 40% → 30%

【適用範圍】
- HEIC 轉 JPG 後自動壓縮
- JPG/PNG 檔案自動壓縮
- PDF 不需要壓縮（用 pdfplumber 解析）

【程式碼位置】
pipeline.py: _compress_image() 函數'''

c.execute('''INSERT OR REPLACE INTO entities (id, type, name, project, agent, body, created, updated) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
          ('skill-image-compress', 'skill', '圖片壓縮規則', 'tw-accounting', 'bookkeeper', rule, now, now))

conn.commit()
print('已新增 skill-image-compress')
