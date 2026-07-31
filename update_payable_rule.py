import sqlite3
conn = sqlite3.connect('C:/Users/user/kiro-graph/graph.db')
c = conn.cursor()

rule_content = """應付帳款欄位規則：

## 憑證類型（D欄）
- 有發票號碼 → 直接填發票號碼（如 AB12345678）
- 沒有發票號碼 → 留空，讓使用者從下拉選單選擇

## 摘要（G欄）
- 格式：廠商簡稱前2字 + 品名/內容
- 例如：「金典 五金材料」、「廣洋 水電材料」
- 不要把發票號碼放在摘要！

## data 格式範例：
{
    "日期": "115/07/31",
    "發票": "AB12345678",      # 有發票就填，會自動放到憑證類型
    "應付類型": "帳款",
    "部門代號": "XZL002",
    "廠商統編": "12345678",
    "廠商簡稱": "金典",
    "品名": "五金材料",        # 會放到摘要
    "含稅額": 1050
}

## 沒有發票的情況：
{
    "日期": "115/07/31",
    "應付類型": "費用",
    "憑證類型": "",            # 留空讓使用者選
    "廠商統編": "12345678",
    "摘要": "辦公用品",
    "含稅額": 500
}"""

c.execute("UPDATE entities SET body = ? WHERE id = 'skill-payable-format'", (rule_content,))
if c.rowcount == 0:
    c.execute("INSERT INTO entities (id, type, name, body, project, created, updated) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
              ('skill-payable-format', 'skill', '應付帳款格式規則', rule_content, 'tw-accounting'))
conn.commit()
print('已更新應付帳款規則')
conn.close()
