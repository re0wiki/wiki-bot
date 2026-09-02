"""批量补全 Module 的 /doc 子页文档（用户已批准）：

- 12 个功能模块：按 Module:Kana2Romaji/doc 体例（导航模板首行 + ; 定义列表），
  Title/Interwiki/NoteTA/WikitextLC/Sandbox 无 Tab 导航模板，直接正文
- 27 个语录数据子表：统一一行说明 + 指回主模块文档
- 已有 /doc 的保留首行导航；NoteTA/doc、WikitextLC/doc 为新建

注意：文档正文的 -{...}- 与 [[en:...]] 示例必须 <nowiki>，分类提及必须前导冒号。
批量编辑（bot flag）。幂等：内容相同则跳过。
"""

import os

os.environ.pop("PYTHONPATH", None)

import pywikibot

site = pywikibot.Site("zh", "re0")

DOCS = {}

DOCS["Init"] = """{{Tab/Init}}
; 说明
页面初始化模块：经 {{T|Init}} 用于几乎每个文章页（限主命名空间，其他空间会 assert 报错）。一次调用输出三段内容。

; 输出
# 标题转换：词干（+后缀）包成 9 变体全写的 <nowiki>-{T|...}-</nowiki>，保证任何语言变体下页面标题按词干显示；
# 自动分类：有后缀 → <nowiki>[[Category:前缀后缀]]</nowiki>（如「角色」+「图库」→ Category:角色图库），仅前缀 → <nowiki>[[Category:前缀]]</nowiki>，都没有 → [[:Category:杂项]]；
# 顶部 tab 导航：当前（主）页 + 各已存在的登记后缀子页，不足 2 个页面时不显示。存在性探测（逐个 title.exists，有缓存）是必要开销——Scribunto 没有子页列举 API。

; 接口
* <code>p.main(frame)</code>：供 <nowiki>{{#invoke:Init|main}}</nowiki>（经 {{T|Init}}）。

标题的前缀/词干/后缀解析依赖 [[Module:Title]]，tab 条拼接依赖 [[Module:Tab]]。
"""

DOCS["Tab"] = """{{Tab/Tab}}
; 说明
顶部分页导航 tab 条的 HTML 拼接：&lt;div class="tabs"&gt; 内每个链接一个 &lt;span class="tab"&gt;。链接不足 2 个时返回空串（单页无需导航）。

; 接口
* <code>p._tab(tabs)</code>：供其他模块调用，参数为链接 wikitext 数组（遇首个空串停止）。[[Module:Init]] 经此接口生成页面导航。
* <code>p.tab(frame)</code>：供 <nowiki>{{#invoke:tab|tab|链接1|链接2|...}}</nowiki>（经 {{T|Tab}}，参数解析依赖 [[w:c:dev:Module:Arguments|Dev:Arguments]]）。
"""

DOCS["Title"] = """; 说明
标题解析模块：把文章页标题拆成「伪命名空间前缀 + 词干 + 子页后缀」三段。[[Module:Init]] 的自动分类与 tab 导航、[[Module:Infobox book]] 的默认书名都依赖它。

; 数据表（均导出）
* <code>p.prefixes</code>：登记的伪命名空间前缀（术语/声优/漫画/存档/角色/音乐/小说/动画/游戏/制作人员/设定集、画集）。'''与 bot 仓库 user-fixes.py 的 PSEUDO_PREFIXES 双维护——改前缀两边都要动。'''
* <code>p.suffixes</code>：登记的子页后缀（经历/关系/梗概/图库/猫语/语录/改动/攻略/短篇）。

; 接口
* <code>p.parse_title(title)</code> → <code>prefix, stem, suffix</code>。未登记的前缀/后缀视为不存在，归入词干（如「小说:佩特拉的爱蜜莉雅阵营奋斗记/page1」的 page1 不是登记后缀，整段留在词干里）。
* <code>p.get_prefix(frame)</code> / <code>p.get_stem(frame)</code> / <code>p.get_suffix(frame)</code>：供 <nowiki>{{#invoke:Title|get_stem|title=...}}</nowiki>。
"""

DOCS["Interwiki"] = """; 说明
从当前页源码提取跨语言链接（如 <nowiki>[[en:...]]</nowiki>），生成带链接的英文名。用于各信息框的「英文名」栏：[[Module:Infobox book]] 直接 require，{{T|Infobox character}}、{{T|Infobox battle}}、{{T|To do}} 经 #invoke 调用。

; 接口
* <code>p.get(prefix, raw)</code>：取当前页首个 <nowiki>[[prefix:...]]</nowiki> 链接。raw 为真返回裸目标名，否则返回带链接的 wikitext；找不到返回空串。
* <code>p.get_en()</code> / <code>p.get_en_raw()</code>：en 的便捷封装，供 <nowiki>{{#invoke:interwiki|get_en}}</nowiki>。
"""

DOCS["Auto ruby"] = """{{Tab/Ruby}}
; 说明
{{T|R}} 的实现：中文名（粗体）+ 可选英文 ruby + 括号内可选日文假名 ruby。罗马字缺省时经 [[Module:Kana2Romaji]] 自动生成；假名完全不可转换时整段日文 ruby 省略。

; 接口
* <code>p.ruby(frame)</code>：供 {{T|R}}。参数 cn（中文名）、en（英文）、kana（假名）、romaji（罗马字，缺省自动转换）。
* <code>p.ruby_ja(frame)</code>：单独的日语 ruby。kana 不可转换时回退为 <nowiki>-{假名}-</nowiki> 原文。
"""

DOCS["Bili"] = """{{Tab/Bili}}
; 说明
{{T|BV}} 的实现：生成 B 站视频嵌入 &lt;div class="BilibiliVideo"&gt;（data-bv/data-av 属性），由全站 JS 替换为播放器；div 内附直链文本兜底。id 首字符为 b/B 判为 BV 号，否则 AV 号。

; 接口
* <code>p.bv(frame)</code>：供 {{T|BV}}。参数 id（BV/AV 号）、page（分 P 序号）。
"""

DOCS["Character image"] = """{{Tab/Character image}}
; 说明
{{T|Infobox character}} 的角色介绍图候选清单生成器：按媒介 × 子分类 × 扩展名（gif/png/jpg/jpeg/webp）穷举「&lt;名字&gt; &lt;媒介&gt; &lt;子分类&gt;角色介绍图.&lt;扩展名&gt;」，模板据此筛出实际存在的图进图库。媒介代码：a 动画 / c 漫画 / g 游戏 / n 文库 / m 其他。子分类随作品增补（新章节、新游戏、新画师）时直接在源码 <code>subs</code> 表追加。

; 接口
* <code>p.gen(frame)</code>：参数 acgnm（媒介代码）、name（角色名）。输出换行分隔的「文件名|显示标签」清单。
"""

DOCS["Infobox book"] = """{{Tab/Infobox book}}
; 说明
{{T|Infobox book}} 的实现：书籍信息框（PortableInfobox）。页数/发售日期/ISBN 三组字段按 12 种语言折叠分组；组内语言按发售日期排序，日期并列（含全空）时按固定语言顺序（ja → 简中 → 繁中 → en → …），保证渲染确定。

; 接口
* <code>p.main(frame)</code>：供 {{T|Infobox book}}。name 缺省取当前页词干（经 [[Module:Title]]），英文名取当前页 <nowiki>[[en:...]]</nowiki> 跨语言链接（经 [[Module:Interwiki]]），其余字段（image、name_ja_kanji、name_ja_romaji、painter、cover、pages_*/date_*/isbn_*）直接透传模板参数。
"""

DOCS["NoteTA"] = """; 说明
标题/全文手工转换模块（{{T|NoteTA}}），移植自维基百科。本站没有 CGroup（Module:CGroup/* 与 Template:CGroup/* 均不存在），G 参数只输出占位 div 由前端 JS 处理。转换标记的生成依赖 [[Module:WikitextLC]]。

; 参数
* <code>T</code>：标题转换规则；<code>dt</code>：其描述；
* <code>G1</code>–<code>G30</code>：公共转换组名（本站仅占位）；
* <code>1</code>–<code>30</code>：全文转换规则；<code>d1</code>–<code>d30</code>：对应描述；
* 以上任一组超过 30 个时归入 [[:Category:NoteTA模板参数使用数量超过限制的页面]]；
* <code>noindicator</code>：不显示右上角转换图标。

; 接口
* <code>z.main(frame)</code>：供 {{T|NoteTA}}；也可由其他模块以参数表直接调用。同页多次调用时 indicator 的 id 用调用序号区分。
"""

DOCS["WikitextLC"] = """; 说明
手工转换（<nowiki>-{...}-</nowiki>）语法生成器，移植自维基百科，[[Module:NoteTA]] 的依赖。

; 接口
* <code>p.selective(content)</code>：按变体表生成 <nowiki>-{zh-cn:...;zh-tw:...;}-</nowiki>（空值转为 &lt;span&gt;&lt;/span&gt;）；
* <code>p.converted(content, variant, force)</code>：限定变体的 <nowiki>-{...|...}-</nowiki>；
* <code>p.raw(content)</code>：<nowiki>-{R|...}-</nowiki> 不转换；
* <code>p.title(content)</code>：<nowiki>-{T|...}-</nowiki> 标题转换；
* <code>p.hidden(content)</code>：<nowiki>-{H|...}-</nowiki> 隐藏转换规则。
"""

DOCS["Sandbox"] = """; 说明
沙盒模块：Lua/Scribunto 试验场，无正式功能，内容随时可能被清空或改写。
"""

DOCS["鼠色猫语录"] = """{{Tab/Author}}
; 说明
鼠色猫（作者长月达平）语录数据库 + 关键词查询，经 {{T|Q}} 用于各 /猫语、/语录 子页。数据按角色/来源拆在 27 个数据子表，主模块每次查询 require 全部子表后逐条过滤。

; 查询
<nowiki>{{#invoke:鼠色猫语录|query|关键词1|关键词2|...}}</nowiki>（经 {{T|Q}}）：位置参数即关键词（对所有文本字段做子串匹配，OR 语义），不传参数输出全部条目。无命中时返回固定提示并归入 [[:Category:模块:鼠色猫语录 查询结果为空]]。

; 数据格式（数据子表）
每个子表导出两个表：
* <code>list</code>：条目数组。字段 <code>src</code>（来源，可经 abbr 缩写）、<code>s/es/js</code>（陈述 中/英/日）、<code>q/eq/jq</code> 与 <code>a/ea/ja</code>（问答对）；译文缺省留空串，展示时非空语言自动收进下拉；
* <code>abbr</code>：来源缩写 → 全称映射。

帕克、福尔图娜、Web连载网站上评论、动画实况解说 4 个空子表是刻意保留的占位（2026-07-30 决策）。
"""

# ── 数据子表：统一一行说明 ────────────────────────────────
CHAR_TABLES = [
    "佩特拉",
    "加菲尔",
    "奥托",
    "威尔海姆",
    "安娜塔西亚",
    "由里乌斯",
    "帕克",
    "库珥修",
    "普莉希拉",
    "特蕾西亚",
    "福尔图娜",
    "约书亚",
    "罗兹瓦尔",
    "罗姆爷",
    "艾姬多娜",
    "艾尔莎",
    "爱蜜莉雅",
    "弗雷德莉卡",
    "莱茵哈鲁特",
    "菲莉丝",
    "菲鲁特",
    "蜜蜜",
]
SRC_TABLES = ["早期ask", "Nico生放送", "动画实况解说", "Web连载网站上评论", "签名会"]
EMPTY_TABLES = {"帕克", "福尔图娜", "Web连载网站上评论", "动画实况解说"}

DATA_DOCS = {}
for name in CHAR_TABLES:
    DATA_DOCS[f"鼠色猫语录/{name}"] = f"{name}相关语录"
for name in SRC_TABLES:
    DATA_DOCS[f"鼠色猫语录/{name}"] = f"来源为{name}的语录"

for title, desc in DATA_DOCS.items():
    empty_note = (
        "当前为空占位（刻意保留）。" if title.split("/")[-1] in EMPTY_TABLES else ""
    )
    DOCS[title] = (
        "{{Tab/Author}}\n"
        f"[[Module:鼠色猫语录]] 的数据子表：{desc}。{empty_note}"
        "格式与字段说明见主模块文档（[[Module:鼠色猫语录/doc]]）。\n"
    )

assert len(DOCS) == 12 + 27, len(DOCS)

# ── 部署 ──────────────────────────────────────────────────
site.login()
assert site.user() == "IchiSanNi"

saved = skipped = 0
for title, text in DOCS.items():
    p = pywikibot.Page(site, "Module:" + title + "/doc")
    if p.exists() and p.text.strip() == text.strip():
        print(f"跳过 {p.title()}（已是最新）")
        skipped += 1
        continue
    p.text = text
    p.save(summary="补全模块文档", bot=True)
    print(f"已保存 {p.title()}")
    saved += 1

print(f"\n共 {saved} 保存 / {skipped} 跳过")
