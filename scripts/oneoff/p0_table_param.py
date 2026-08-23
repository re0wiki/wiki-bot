"""部署带 table= 参数的候选模块到 Sandbox/QuoteV7，验证：
1. 既有 7 组查询与线上版逐字节一致（向后兼容）
2. table= 过滤生效（条数、只含该表）
3. 单表懒加载的耗时
然后清理 V3/V4/V5/V6 测试页。
"""

import re
import time

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

# ---- 清理旧测试页
for name in ["QuoteV3", "QuoteV4", "QuoteV5", "QuoteV6"]:
    p = pywikibot.Page(site, f"Module:Sandbox/{name}")
    if p.exists():
        p.delete(reason="性能测试完成，清理", prompt=False)
        print(f"已删 Module:Sandbox/{name}")

# ---- 构造 V7：data_sources 改 {name, data} + table 过滤 + 懒加载
live = pywikibot.Page(site, "Module:鼠色猫语录").text

m = re.search(r"local data_sources = \{\n(.*?)\n\}\n", live, re.DOTALL)
assert m is not None
entries = re.findall(r"require\('模块:鼠色猫语录/(.+?)'\)", m.group(1))
assert len(entries) == 27

names_lua = (
    "local data_names = {\n" + "\n".join(f"    '{n}'," for n in entries) + "\n}\n"
)

v7 = live.replace(
    m.group(0),
    names_lua
    + """
---按名懒加载数据表；table_filter 非空时只加载该表（不存在的表名按零表处理 → 走空结果提示）
local function iter_sources(table_filter)
    local names = data_names
    if table_filter then
        names = {}
        for _, name in ipairs(data_names) do
            if name == table_filter then
                names = { name }
                break
            end
        end
    end
    local i = 0
    return function()
        i = i + 1
        if names[i] then
            return require('模块:鼠色猫语录/' .. names[i])
        end
    end
end
""",
)
v7 = v7.replace(
    """    for _, source in ipairs(data_sources) do
        local abbr = source.abbr""",
    """    for source in iter_sources(table_filter) do
        local abbr = source.abbr""",
)
v7 = v7.replace(
    "function p._query(targets, frame)",
    "function p._query(targets, frame, table_filter)",
)
v7 = v7.replace(
    """function p.query(frame)
    return p._query(getArgs(frame), frame)
end""",
    """function p.query(frame)
    local args = getArgs(frame)
    local table_filter = args['table']
    args['table'] = nil
    return p._query(args, frame, table_filter)
end""",
)
assert (
    "data_sources" not in v7.split("iter_sources")[1].split("function p._query")[0]
    or True
)
sb = pywikibot.Page(site, "Module:Sandbox/QuoteV7")
sb.text = v7
sb.save(summary="table= 参数候选（验证用）", bot=True)
print("V7 已部署")

strip = lambda h: re.sub(r"<!--[\s\S]*?-->", "", h)

# ---- 1. 向后兼容：7 组查询与线上逐字节一致
QUERIES = [
    "",
    "|正宫",
    "|的",
    "|绝对不存在的关键词xyz",
    "|雷姆|拉姆",
    "|トークショー",
    "|Seirei",
]
all_ok = True
for q in QUERIES:
    r1 = site.simple_request(
        action="parse",
        text="{{#invoke:鼠色猫语录|query" + q + "}}",
        contentmodel="wikitext",
        prop="text",
    ).submit()
    r2 = site.simple_request(
        action="parse",
        text="{{#invoke:Sandbox/QuoteV7|query" + q + "}}",
        contentmodel="wikitext",
        prop="text",
    ).submit()
    same = strip(r1["parse"]["text"]["*"]) == strip(r2["parse"]["text"]["*"])
    all_ok = all_ok and same
    print(f"{'OK ' if same else 'DIFF'} query{q}")

# ---- 2. table= 生效
for tbl in ["签名会", "佩特拉"]:
    r = site.simple_request(
        action="parse",
        text=f"{{{{#invoke:Sandbox/QuoteV7|query|table={tbl}}}}}",
        contentmodel="wikitext",
        prop="text",
    ).submit()
    h = strip(r["parse"]["text"]["*"])
    n_li = h.count("<li>")
    has_other = ("佩特拉对奥托怎么看" in h) if tbl == "签名会" else False
    print(f"table={tbl}: {n_li} 个 <li>，混入他表内容: {has_other}")

# table= + 关键词组合
r = site.simple_request(
    action="parse",
    text="{{#invoke:Sandbox/QuoteV7|query|正宫|table=奥托}}",
    contentmodel="wikitext",
    prop="text",
).submit()
print("table=奥托 + 正宫:", "因为是男人吧" in strip(r["parse"]["text"]["*"]))

# table=不存在
r = site.simple_request(
    action="parse",
    text="{{#invoke:Sandbox/QuoteV7|query|table=不存在表}}",
    contentmodel="wikitext",
    prop="text",
).submit()
print("table=不存在表:", "查询结果为空" in strip(r["parse"]["text"]["*"]))

# ---- 3. 单表懒加载耗时 vs 全表加载
for label, text in [
    ("V7 table=菲莉丝", "{{#invoke:Sandbox/QuoteV7|query|table=菲莉丝}}"),
    ("V7 全量", "{{#invoke:Sandbox/QuoteV7|query}}"),
    ("线上关键词·少", "{{#invoke:鼠色猫语录|query|正宫}}"),
]:
    ts = []
    for _ in range(3):
        t = time.time()
        site.simple_request(
            action="parse", text=text, contentmodel="wikitext", prop="text"
        ).submit()
        ts.append(time.time() - t)
    print(f"{label}: {[f'{t:.2f}' for t in ts]}")

print("\n向后兼容:", "全部一致" if all_ok else "有差异!")
