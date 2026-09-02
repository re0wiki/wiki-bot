"""一次性：精简 Module:Wiki-navigation 注释（与 doc 去重），清理 doc 中的仓库历史信息。"""

import pywikibot

LUA = """local p = {}

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

DOC = """; 说明
实时编译导航栏：读取 [[Project:Wiki-navigation]] 的源码，编译为 [[MediaWiki:Wiki-navigation]] 所需的导航语法（后者内容仅为 <nowiki>{{#invoke:Wiki-navigation|main}}</nowiki>）。

; 编译规则
逐行处理源页：
# 非 <code>*</code> 开头的行丢弃；
# <code>*</code> 前缀追加「*** 」（Project 页 N 级 → 导航 N+3 级）；
# 词干含 <code>[</code> 时剥去所有方括号（即拆掉链接，保留「目标|显示文本」形态）；
# 词干含 <code>|</code> 时原样保留；
# 否则补「|」前缀（导航语法要求词干以 | 开头表示无链接项）。

; 接口
* <code>p.main()</code>：供 <nowiki>{{#invoke:Wiki-navigation|main}}</nowiki>。

; 注意事项
* 缓存依赖：mw.title.getContent 会把 Project:Wiki-navigation 登记进 MediaWiki:Wiki-navigation 的 templatelinks，源页编辑后消息的解析缓存即失效；Fandom 导航服务自身缓存的刷新延迟可能再叠加一段时间。
* '''模块返回值不会被二次展开模板'''：导航源里写模板会原样漏出，须直接写展开后的内容（如 {{T|Seirei}} 已内联为 <code><nowiki>精<!--nobot-->灵</nowiki></code>）。
* 源页编辑规定与导航结构说明见 [[Project:Wiki-navigation]] 页首。
"""

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

module = pywikibot.Page(site, "Module:Wiki-navigation")
assert module.text != LUA
module.text = LUA
module.save(summary="精简注释：与 doc 子页去重", bot=False, minor=False)
print("module updated")

doc = pywikibot.Page(site, "Module:Wiki-navigation/doc")
assert doc.text != DOC
doc.text = DOC
doc.save(summary="清理仓库历史变更信息", bot=False, minor=False)
print("doc updated")
