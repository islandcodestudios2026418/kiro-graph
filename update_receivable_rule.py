import sqlite3
conn = sqlite3.connect('C:/Users/user/kiro-graph/graph.db')
c = conn.cursor()

rule_content = """應收帳款欄位規則：
- AI 辨識發票 → 只填「含稅金額」欄位
- 「未稅金額」欄位留空（人工輸入才用）
- 必填欄位：發票日期、發票號碼、客戶名稱、摘要、含稅金額
- 可選欄位：報價日期、請款日期、部門名稱、備註

data 格式範例：
{
    "發票日期": "115/07/31",
    "發票": "AB12345678",
    "客戶名稱": "全聯",
    "客戶統編": "12345678",
    "摘要": "銷貨",
    "含稅金額": 1050
}

注意：不要傳「未稅金額」和「稅額」，只傳「含稅金額」！"""

c.execute("UPDATE entities SET body = ? WHERE id = 'skill-receivable-format'", (rule_content,))
if c.rowcount == 0:
    c.execute("INSERT INTO entities (id, type, name, body, project, created, updated) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
              ('skill-receivable-format', 'skill', '應收帳款格式規則', rule_content, 'tw-accounting'))
conn.commit()
print('已更新應收帳款規則')
conn.close()
