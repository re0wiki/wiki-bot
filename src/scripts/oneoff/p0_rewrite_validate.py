"""部署重写候选到 Module:Sandbox/QuoteV2 并做渲染等价验证（parse 输出逐字节对比）。

Sandbox 子页面在写入红线内（任意命名空间的 Sandbox 子页）。
"""

import re
import time

import pywikibot

NEW_MODULE = r"""local p = {}

local getArgs = require('Dev:Arguments').getArgs

local data_sources = {
    require('模块:鼠色猫语录/佩特拉'),
    require('模块:鼠色猫语录/加菲尔'),
    require('模块:鼠色猫语录/奥托'),
    require('模块:鼠色猫语录/威尔海姆'),
    require('模块:鼠色猫语录/安娜塔西亚'),
    require('模块:鼠色猫语录/由里乌斯'),
    require('模块:鼠色猫语录/帕克'),
    require('模块:鼠色猫语录/库珥修'),
    require('模块:鼠色猫语录/普莉希拉'),
    require('模块:鼠色猫语录/特蕾西亚'),
    require('模块:鼠色猫语录/福尔图娜'),
    require('模块:鼠色猫语录/约书亚'),
    require('模块:鼠色猫语录/罗兹瓦尔'),
    require('模块:鼠色猫语录/罗姆爷'),
    require('模块:鼠色猫语录/艾姬多娜'),
    require('模块:鼠色猫语录/艾尔莎'),
    require('模块:鼠色猫语录/爱蜜莉雅'),
    require('模块:鼠色猫语录/弗雷德莉卡'),
    require('模块:鼠色猫语录/莱茵哈鲁特'),
    require('模块:鼠色猫语录/菲莉丝'),
    require('模块:鼠色猫语录/菲鲁特'),
    require('模块:鼠色猫语录/蜜蜜'),
    require('模块:鼠色猫语录/早期ask'),
    require('模块:鼠色猫语录/Nico生放送'),
    require('模块:鼠色猫语录/动画实况解说'),
    require('模块:鼠色猫语录/Web连载网站上评论'),
    require('模块:鼠色猫语录/签名会'),
}

---targets 中任一字符串是 s 的子串即命中（targets 为空时命中全部）
local function any_in(targets, s)
    if not targets[1] then
        return true
    end
    for _, target in ipairs(targets) do
        if mw.ustring.find(s, target, 1, true) then
            return true
        end
    end
    return false
end

---生成一个内容块（陈述/问/答）：首个非空语言直接显示，其余收进下拉
local function content_html(prefix, zh, en, ja)
    local first
    local rest = {}
    for _, content in ipairs { zh, en, ja } do
        if content ~= '' then
            if first then
                table.insert(rest, content)
            else
                first = content
            end
        end
    end
    if not first then
        return ''
    end
    if prefix then
        first = ("'''%s'''：%s"):format(prefix, first)
    end
    if not rest[1] then
        return '<br/>' .. first
    end
    return '<br/><div class="wds-dropdown ruby-tooltip"><div class="wds-dropdown__toggle">'
        .. first
        .. '</div><div class="wds-dropdown__content">'
        .. table.concat(rest, '<hr/>')
        .. '</div></div>'
end

---@param targets table
---@param frame table
function p._query(targets, frame)
    local buf = {}
    local cnt = 0

    for _, source in ipairs(data_sources) do
        local abbr = source.abbr
        for _, data in ipairs(source.list) do
            local src = abbr[data.src] or data.src

            local s = data.s or ''
            local es = data.es or ''
            local js = data.js or ''

            local q = data.q or ''
            local eq = data.eq or ''
            local jq = data.jq or ''

            local a = data.a or ''
            local ea = data.ea or ''
            local ja = data.ja or ''

            if any_in(targets, src
                    .. s .. es .. js
                    .. q .. eq .. jq
                    .. a .. ea .. ja) then
                cnt = cnt + 1
                buf[cnt] = '<li><small>' .. src .. '</small>'
                    .. content_html(nil, s, es, js)
                    .. content_html('Q', q, eq, jq)
                    .. content_html('A', a, ea, ja)
                    .. '</li>'
            end
        end
    end

    if cnt == 0 then
        return '『[[模块:鼠色猫语录]] 查询结果为空』[[分类:模块:鼠色猫语录 查询结果为空]]'
    end
    return frame:preprocess('<ol>' .. table.concat(buf) .. '</ol>')
end

function p.query(frame)
    return p._query(getArgs(frame), frame)
end

return p
"""

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

sandbox = pywikibot.Page(site, "Module:Sandbox/QuoteV2")
sandbox.text = NEW_MODULE
sandbox.save(summary="语录查询模块重写候选（性能优化），渲染等价验证用", bot=True)
print("sandbox 已部署")

QUERIES = [
    "{{#invoke:鼠色猫语录|query}}",
    "{{#invoke:鼠色猫语录|query|正宫}}",
    "{{#invoke:鼠色猫语录|query|的}}",
    "{{#invoke:鼠色猫语录|query|绝对不存在的关键词xyz}}",
    "{{#invoke:鼠色猫语录|query|雷姆|拉姆}}",
    "{{#invoke:鼠色猫语录|query|トークショー}}",
    "{{#invoke:鼠色猫语录|query|Seirei}}",
]

time.sleep(2)
all_ok = True
for q in QUERIES:
    q2 = q.replace("鼠色猫语录", "Sandbox/QuoteV2")
    r1 = site.simple_request(
        action="parse", text=q, contentmodel="wikitext", prop="text"
    ).submit()
    r2 = site.simple_request(
        action="parse", text=q2, contentmodel="wikitext", prop="text"
    ).submit()
    h1 = r1["parse"]["text"]["*"]
    h2 = r2["parse"]["text"]["*"]
    # 剥掉所有 HTML 注释（limit report 等逐次元数据噪声；两侧同等处理不影响内容对比）
    strip = lambda h: re.sub(r"<!--[\s\S]*?-->", "", h)
    h1n = strip(h1)
    h2n = strip(h2)
    same = h1n == h2n
    all_ok = all_ok and same
    print(f"{'OK ' if same else 'DIFF'} {q}  ({len(h1)} vs {len(h2)} bytes)")
    if not same:
        # 找第一处差异
        for i, (c1, c2) in enumerate(zip(h1, h2)):
            if c1 != c2:
                print(
                    f"  首个差异@{i}: 旧 {h1[i - 40 : i + 40]!r} 新 {h2[i - 40 : i + 40]!r}"
                )
                break

# 性能对比
print()
for label, q in [("命中多", "|query|的}}"), ("全量", "|query}}")]:
    for mod in ["鼠色猫语录", "Sandbox/QuoteV2"]:
        ts = []
        for _ in range(3):
            t0 = time.time()
            site.simple_request(
                action="parse",
                text="{{#invoke:" + mod + q,
                contentmodel="wikitext",
                prop="text",
            ).submit()
            ts.append(time.time() - t0)
        print(f"{label} {mod}: {[f'{t:.1f}s' for t in ts]}")

print("\n全部一致" if all_ok else "\n存在差异！")
