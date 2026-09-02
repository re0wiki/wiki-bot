"""一次性：创建 Module:Wiki-navigation/doc。"""

import pywikibot

DOC = """; 说明
实时编译导航栏：读取 [[Project:Wiki-navigation]] 的源码，编译为 [[MediaWiki:Wiki-navigation]] 所需的导航语法（后者内容仅为 <nowiki>{{#invoke:Wiki-navigation|main}}</nowiki>）。2026-08-16 起取代 bot 定期编译任务（原脚本 re0_nav.py 已随仓库 dev 分支删除）。

; 编译规则
逐行处理源页，规则与 re0_nav.py 的 compile_line 一一对应：
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

doc = pywikibot.Page(site, "Module:Wiki-navigation/doc")
assert not doc.exists(), "doc 已存在"
doc.text = DOC
doc.save(summary="创建模块文档", bot=False, minor=False)
print("doc saved")
