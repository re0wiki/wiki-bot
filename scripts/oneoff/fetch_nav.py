"""一次性：创建 Module:Wiki-navigation 并验证其展开输出与 compile_nav 逐字节一致。"""

import difflib

from pywikibot.data import api

import pywikibot

LUA = """-- 实时编译 [[Project:Wiki-navigation]] 为 [[MediaWiki:Wiki-navigation]] 所需的导航语法。
-- 取代原 bot 定期编译任务（re0_nav.py）；MediaWiki:Wiki-navigation 内容为 {{#invoke:Wiki-navigation|main}}。
-- 编译规则与 re0_nav.py 的 compile_line 一一对应：
--   非 * 开头的行丢弃；* 前缀追加 "*** "（Project 页 N 级 -> 导航 N+3 级）；
--   词干含 [ 时剥去所有方括号；含 | 时原样保留；否则补 "|" 前缀。

local p = {}

local function compileLine(line)
    line = line:gsub('\\r$', '')
    if line:sub(1, 1) ~= '*' then
        return nil
    end
    local i = line:find(' ', 1, true)
    if not i then
        return nil
    end
    local prefix = line:sub(1, i - 1) .. '*** '
    local stem = line:sub(i + 1)
    if stem:find('[', 1, true) then
        return prefix .. stem:gsub('[%[%]]', '')
    end
    if stem:find('|', 1, true) then
        return prefix .. stem
    end
    return prefix .. '|' .. stem
end

function p.main()
    local src = mw.title.new('Project:Wiki-navigation'):getContent()
    if not src then
        return ''
    end
    local out = {}
    for _, line in ipairs(mw.text.split(src, '\\n')) do
        local c = compileLine(line)
        if c then
            out[#out + 1] = c
        end
    end
    return table.concat(out, '\\n')
end

return p
"""


def compile_line(line: str) -> str:
    if not line.startswith("*"):
        return ""
    prefix, stem = line.split(" ", 1)
    prefix += "*** "
    if "[" in stem:
        return prefix + stem.replace("[", "").replace("]", "")
    if "|" in stem:
        return prefix + stem
    return prefix + "|" + stem


def compile_nav_content(src: str) -> str:
    return "\n".join(c for line in src.splitlines() if (c := compile_line(line)))


site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

module = pywikibot.Page(site, "Module:Wiki-navigation")
if module.text != LUA:
    module.text = LUA
    module.save(
        summary="创建：实时编译 Project:Wiki-navigation，取代 bot 定期编译",
        bot=False,
        minor=False,
    )
    print("module saved")
else:
    print("module already up to date")

# expandtemplates 执行 #invoke 但不渲染 HTML，用于字节级比对
req = api.Request(
    site=site,
    parameters={
        "action": "expandtemplates",
        "text": "{{#invoke:Wiki-navigation|main}}",
        "prop": "wikitext",
    },
)
expanded = req.submit()["expandtemplates"]["wikitext"]

src = pywikibot.Page(site, "Project:Wiki-navigation").text
expected = compile_nav_content(src)
print("expanded == compiled:", expanded == expected)
if expanded != expected:
    print("expanded len:", len(expanded), "| expected len:", len(expected))
    for line in difflib.unified_diff(
        expected.splitlines(),
        expanded.splitlines(),
        "expected",
        "expanded",
        lineterm="",
    ):
        print(line)
