---
name: wiki-access
description: "Use when 读写 re0 wiki 或编写任何 wiki 交互代码（含一次性脚本、裸 API）。读写配方、限速、实测坑。"
version: 1.0.0
---

# wiki 读写配方（pywikibot 库方式 + 裸 API）

读写 rezero.fandom.com（re0 family，12 个语言子站）的实测用法与坑。
安全红线、环境要求和最小用法见 `AGENTS.md`「读写 wiki」一节；本文档是完整配方。

## 读

```python
import pywikibot

site = pywikibot.Site("zh", "re0")   # 其他语言站: Site("en", "re0") 等

p = pywikibot.Page(site, "角色:菜月·昴")
p.exists()            # bool
p.text                # wikitext 全文
p.isRedirectPage()    # bool
p.getRedirectTarget() # 重定向目标 Page（注意: 本 wiki 重定向写作 #REDIRECT 而非 #重定向）
p.namespace()         # 命名空间对象，str() 得到名字（主命名空间是空串）

# 历史版本
for rev in p.revisions(total=2):
    rev.timestamp, rev.user, rev.comment, rev.text  # rev.text 是该版本全文
```

`pywikibot.Page(site, title)` 构造本身不发请求，访问 `.text` 才发。

## 写

```python
site.login()  # 写入前必须；纯读取可以不登录
assert site.user() == "IchiSanNi"

p = pywikibot.Page(site, "User:IchiSanNi/沙盒")
p.text = p.text + "\n追加内容\n"
p.save(summary="编辑摘要", bot=False, minor=False)  # 手动编辑：bot/minor 都必须显式关
p.save(summary="编辑摘要", bot=True)                # 批量脚本：加 bot=True（或 p.put(...)）
```

- **bot flag 的取舍**：bot flag 会阻止常规通知机制（避免批量编辑刷屏）。跑批量脚本时用 `bot=True` 没问题；但手动编辑特定页面时，操作更接近需人工审查的常规编辑，**不要加 bot flag**。
- **pywikibot ≥9.4 起 `save()` 默认 `bot=True, minor=True`**（None 选项已移除）——手动编辑不显式传 `bot=False, minor=False` 就会被标成 bot 小编辑，且 bot/minor 标记事后无法摘除（只能等滚出 recentchanges）。
- 验证 bot flag 要查 `list=recentchanges`（rcprop=flags）；`usercontribs` 的 ucprop=flags **不返回 bot 键**（即使编辑带 bot flag），会漏报。
- `botflag=` 参数已废弃，用 `bot=`；传了 botflag 只会触发 FutureWarning，不影响保存。
- save 有内置异常保护；批量写建议 try `pywikibot.exceptions.PageSaveError`。

## 生成器（pagegenerators）

```python
from itertools import islice
from pywikibot import pagegenerators

# 全文搜索 —— 注意 Fandom 不支持 intitle: 前缀语法（实测返回空），用普通关键词
pagegenerators.SearchPageGenerator("菜月昴", site=site, total=5)

# 分类成员（含子分类用 cat.subcategories()）
cat = pywikibot.Category(site, "Category:新搬运待整理")
cat.articles(total=10)            # total= 在这里生效
cat.categoryinfo["size"]          # 成员数

# 最近更改（注意大小写: RecentChangesPageGenerator）
pagegenerators.RecentChangesPageGenerator(site=site, total=10)

# 链入页面 —— 坑: backlinks(total=N) 的 total 不生效（实测 total=3 返回 31 条），用 islice
list(islice(pywikibot.Page(site, "角色:菜月·昴").backlinks(), 10))

# 模板引用页（embeddedin 的 total= 生效）
list(pywikibot.Page(site, "Template:Init").embeddedin(total=10))

# 按前缀枚举 —— 用 PrefixingPageGenerator（内部走 apprefix，严格限定前缀）
pagegenerators.PrefixingPageGenerator(prefix="小说:", namespace=0, site=site, filterredir=False)
```

- **坑：`AllpagesPageGenerator(start=前缀, total=N)` 不是前缀枚举**——`start` 只是字典序下界游标（上游文档原文 "pages >= this title"），`total` 仅是数量上限，枚举会越过前缀边界继续扫排序在后的全部页面。按前缀枚举一律用 `PrefixingPageGenerator`；`AllpagesPageGenerator` 要设终点只能用 11.4+ 的 `until=`（字典序上界，前缀语义需自行拼上界字符串，不如 Prefixing 直接）。

### 批量取内容：PreloadingGenerator

在生成器循环里直接访问 `page.text` 是**逐页一次请求**（RTT 锁死 ~3.8 req/s，全站扫描要近一小时）。套一层 `PreloadingGenerator` 即批量预取——内部走 `titles=` 50 个/批的 `prop=revisions` 查询（即实测坑节所述两阶段 dump 配方的库内封装）：

```python
from pywikibot import pagegenerators

gen = pagegenerators.AllpagesPageGenerator(site=site, namespace=0)
for page in pagegenerators.PreloadingGenerator(gen, groupsize=50):
    page.text  # 已随批预取，不再发请求
```

- 保持默认 `groupsize=50`（也是 `PreloadingGenerator` 的默认值）：content 查询 >50/批 有静默截断风险（见实测坑节），且 apihighlimits 的 500/批 prop 查询在会话被踢时间歇失败。
- 它**没有截断兜底断言**——全站 dump 级任务（要断言「抓取页数 ≥ siteinfo articles 数」）仍用手搓两阶段配方；日常「扫生成器结果读源码」用它即可。
- 多站点混合生成器（如 interwiki 结果）也支持：内部按 site 分组各自成批。

## 裸 API（库没封装的功能走这里）

```python
# simple_request 复用 pywikibot 的已认证会话和重试逻辑
req = site.simple_request(action="query", list="allpages",
                          apprefix="译名表", apnamespace=4, aplimit=5)
data = req.submit()   # dict
# 注意: apprefix 不含命名空间前缀，命名空间用 apnamespace 单独指定

# 模板/解析器函数展开
site.expand_text("{{NUMBEROFPAGES}}", title="任意页名")
```

对照表：MediaWiki API action ↔ pywikibot 方法见 `pwb/docs/mwapi.rst`。

## 裸 requests + BotPassword（逃生舱的逃生舱，一般不推荐）

优先库方式；simple_request 也解决不了的，再裸调 `https://rezero.fandom.com/zh/api.php`。
裸调（curl / urllib / requests）**必须显式带 User-Agent**，否则 Fandom 直接 403（2026-08-18 实测 urllib 默认 UA 被拒，curl 加 `-A` 即通）。
凭据解析（不读不打印内容，eval 提取 BotPassword 对象）：

```python
from pathlib import Path
from pywikibot.login import BotPassword

entries = []
for line in Path("user-password.py").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line.startswith("("):
        entries.append(eval(line, {"BotPassword": BotPassword}))  # noqa: S307
username, bp = entries[0]
login_name = bp.login_name(username)  # → "IchiSanNi@pywikibot"
```

流程：GET login token → POST login（lgname/lgpassword/lgtoken）→ GET csrf token → POST edit
（token=csrf, bot="1"）。login token 和 csrf token 分两次取（批量取实测可用，但分开无副作用，保持惯例）。
加 `formatversion=2` 可让响应没有数字键，解析更干净。完整可跑代码见 `src/tools/verify_wiki_access.py`。
**login POST 也必须走带 429 退避的重试封装**，不能裸发——否则一被限速连登录都过不去（实测踩过）。

## Fandom 外部视频（video/youtube）导入

Fandom 的「从 YouTube 导入视频」不是文件上传，产出的是无扩展名的伪文件页
（`mime=video/youtube`，文件实体只有缩略图，真实播放走 YouTube embed）。
pywikibot `FilePage` 构造对无扩展名标题直接 `ValueError`，跨站搬运必须走
Fandom 自己的导入端点（Special:NewFiles「添加视频」按钮的前端调用，见
ResourceLoader 模块 `ext.fandom.specialVideos.js`；Nirvana 内部接口，无文档）：

```python
from urllib.parse import urlencode
from pywikibot.comms import http

uri = site.scriptpath() + "/wikia.php?" + urlencode(
    {"controller": r"Fandom\Video\IngestionController", "method": "uploadVideo"}
)
r = http.request(site, uri, method="POST",  # 复用 pywikibot 已登录会话
                 data={"url": f"https://www.youtube.com/watch?v={video_id}",
                       "token": <新鲜 csrf token>})
# 成功: {"status": "Your video has been added.", "success": true}
# 失败: HTTP 400 {"status": 400, "error": "...BadRequestException", "details": ...}
```

实测要点（2026-09-11）：

- en 侧视频的 YouTube `videoId` 从 `prop=imageinfo&iiprop=metadata` 匿名读
  （metadata 里还有 duration）。全部识别口径：`list=allimages&aiprop=mime`
  过滤 `video/youtube`。
- 创建的文件页**标题与正文自动取自 YouTube 当前值**（标题=视频标题、
  正文=视频简介），日志 comment 固定「视频已创建」。
- **标题冲突不覆盖也不报错**：目标标题已存在（哪怕只是重定向页）时自动
  加 `-2` 后缀另建——要按原名重建必须先删掉占位页。
- 端点可能是异步的：success 返回后 imageinfo 立即可查（实测同步生效），
  但若查不到等几秒再查。
- **csrf token 必须现取，不能用 `site.tokens["csrf"]` 的缓存**：token 绑定
  会话，Fandom 跨站流量互踢后 pywikibot 自愈重登换新会话，TokenWallet
  缓存不感知轮换，继续发旧 token 会被 400「Request must be POSTed and
  provide a valid edit token」；裸调 `meta=tokens&type=csrf`（simple_request）
  则先经 userinfo 比对触发自愈重登、返回新会话 token（re0_image 的
  `fresh_csrf()`）。token 类失败重取后重试一次即可恢复。

## 实测结论与坑

- 搜索"菜月昴"能命中 `角色:菜月·昴` 等页（Fandom 搜索对别名友好），但 `intitle:` 语法无效；`insource:` 也不支持（`site.search('insource:"Init"')` 返回 0 但字符串其实遍地都是）。信任任何搜索语法前先用已知真/已知假查询 sanity check。2026-08-19 再踩：`insource:/\{\{To do\|/` 返回 0 而源码扫描实测 107 页带参数——且当时手里就有已知真样本（13 卷刚写入的 `{{To do|由 K3 翻译…}}`）却没拿它验证查询。**查模板/文本用法的权威方式只有扫源码**（categorymembers/allpages 枚举 + `rvprop=content` ≤50/批），搜索语法返回 0 一律视为「查询不可信」而非「不存在」。
- **Fandom 派生表（langlinks 等）的读取可能与页面源码不一致，且与 HTTP 缓存无关**（api.php 响应头 `no-store`、无 Age/X-Cache，已实证排除 CDN 缓存）。2026-08-08 观测：langlinks 对希洛洛返回过源码史上从未存在的值（Toneriko，115 个修订逐版验证源码始终是 Tonerico）、对菜月父母返回过「无 en 链接」（实际 2021-02 起就有，当天两页零编辑），数小时后零编辑自愈——指向 Fandom 基础设施侧的派生表重建/迁移，外部无法定位。**审计「页面有没有某链接/某分类」一律扫源码（rvprop=content），不依赖 langlinks/categories 等派生表**。
- **上一条只适用于 zh 站；en 站正相反——en 页面的类型分类（Characters/Terminology/Re:Zero Volumes 等）大多由 portable infobox 等模板带入，源码里看不到分类行**（2026-09-25 全量 dump 实证：1355/1877 en 内容页源码零分类行、prop=categories 有分类）。查 en 页面分类只能 `prop=categories`（要重定向最终目标的分类时加 `redirects=1`），扫源码无效。差异根源：zh 分类由 Module:Init 按前缀在源码层带入，en 分类在模板层带入。
- **信息框参数里的 `[[链接]]` 不进 links 表**（2026-08-13 实证：当时的 动画:第79集 等 4 页源码含 `| previous = [[X]]` 而 prop=links 无；2026-08-21 沙盒复证实证：新保存页面仅含 portable `<infobox>` 参数链接，等 60s 排除 job queue 延迟后 links 表仍为空）。机制是 portable infobox 扩展渲染参数值时不登记链接，与 #invoke 无关——`{{Init}}` 等 #invoke **输出**里的链接正常登记（同日实证：动画:第50集 links 表含 Init/Tab 模板族输出的子页链接，其 infobox 参数链接 小说:15卷 亦由模板输出带入）。`linkedPages()`/`prop=links`/`linkshere` 对 infobox 参数链接系统性漏报，依赖它们的工具（如上游 fixing_redirects）会永远漏改。链接审计/改写必须扫源码。其余任务已审计无此险（2026-08-13）：category remove/template replace（被操作对象均顶层调用）、redirect-do/br（redirect 表抽查一致）、interwiki/replace 各 fix/re0_move/noreferences（均源码驱动）。
- `site.isInterwikiLink()` 会为命中的跨站前缀**构造目标 APISite**，其 `__init__` 固定 `login(cookie_only=True)` 发 userinfo 请求（zh 站 interwikimap 有 135 个外站前缀，wikipedia/wp 等指向 en.wikipedia.org；2026-09-05 实测墙内不可达，re0_fixing_redirects 每轮运行 SSL 重试直至崩溃）。判断「链接是否跨站」用 re0_fixing_redirects 的 `is_interwiki()`（只比前缀、零外站请求），不要调库方法。
- Fandom API **不支持** `list=mostlinkedtemplates`；查模板引用量改用 `Page.embeddedin(total=N)` 逐个查。
- `api.QueryGenerator` 带 `generator=` 时**逐页 yield page dict**（不是 `{"query": {"pages": {...}}}` 包裹结构）；不带 generator 时才是整包响应。解析前先确认用的是哪种形态。
- `allcategories` 不支持 `acsort` 参数，返回条目也没有 `size` 键；分类规模用 `Category.categoryinfo`。
- `site.namespaces` 迭代返回的是 int 键，取对象用 `site.namespaces[ns_id]`。
- `Page.getVersionHistory()` 在 11.x 不存在；最新版本用 `page.latest_revision`，最早版本用裸 API（`rvdir=newer, rvlimit=1`）。
- `Page.isRedirectPage()` 对 `#重定向 [[...]]` 的页面可能误报 `False`——信 wikitext 不信标志位。
- **`embeddedin`/templatelinks = 0 不等于没人用**：`#tag:` 扩展内容和死模板 `<includeonly>` 里的调用不入 templatelinks。模板删除前审计流程（全站 dump 配方、分类法、删除清单）见 template-usage-audit skill。
- `RecentChangesPageGenerator` 返回有重复条目（同一编辑出现多次），统计时需去重。
- MediaWiki API `formatversion=2` 下 recentchanges 的 `bot`/`new`/`minor` 键**恒存在**（值为 true/false），过滤必须判断值而不是键存在性——`"bot" not in c` 会把所有编辑都滤掉。
- `generator=allpages` 配 `rvprop=content` 会被 Fandom 静默丢弃大部分页面的 revisions（只回页面壳、无报错、无截断提示，实测 2227 页只取回 253 页源码）。全站取源码用两阶段：先 `list=allpages` 枚举标题，再 `titles=` 按 50 个/批取 content。
  - 2026-08-18 复测：经 `api.QueryGenerator` 全量取回 10157/10157 页源码（与 `list=allpages` 标题集交叉验证零缺失）；同任务手搓 continue 分页（gaplimit=500 + content）则遇到某批响应缺 `continue` 字段静默截断（764/2206）。机制（`data/api/_generators.py`）：QueryGenerator 对 content 查询把批大小压到 `api_limit//10` 且 ≤250（匿名=50），上游注释明言 500/批 content 查询「sometimes result in server-side errors」——截断的触发条件是**响应体积**，不是分页协议；缺 continue 时 pywikibot 同样只能 break（协议无信号，任何客户端都检测不了）。结论：content 批查询手搓也压到 ≤50/批，并以「抓取页数 >= siteinfo articles 数」兜底断言截断（`src/tools/audit_wikipedia_links.py` 有此断言）。
- `titles=` 大批（50 个）请求偶发返回 **HTTP 400 空响应体**（非毒标题——二分后每个子批都 200；也非 URL 超长）。降批到 25 + 指数退避重试即可，全量 dump 1 万页级别稳定。
- **PreloadingGenerator 预取的是快照，不是实时状态**：page 对象的 `isRedirectPage()`/`exists()`/`text` 全是预取时刻（批=50 提前抓取）的值。同轮任务内自己移动/编辑过的页面，后续轮到其旧标题对象时缓存检查返回操作前的状态——re0_move 实证（2026-09-25）：父页 `page.move(movesubpages=True)` 联动后，旧子页标题已成重定向，但预加载缓存的 `isRedirectPage()` 仍是 False，脚本把遗留重定向当内容页移走、抢占了全归一目标标题。**同轮有副作用（移动/编辑/联动副作用）的任务必须自记已操作标题并显式排除**（re0_move 的 `moved_sources` + `is_leftover`），不能信预加载缓存。
- 主空间 `allpages` 按字母序，CJK 前缀排在英文之后——采样统计前缀分布必须扫全量。
- 写沙盒后可用 `curl 'https://rezero.fandom.com/zh/api.php?action=query&prop=revisions&titles=...&rvprop=content&rvslots=main&format=json'` 匿名验证结果。
- **Fandom 登录会话对读路径不可靠**（2026-08-13 实证）：cookie jar 会话会被同账号的跨语言站流量服务端作废（互踢，见 user-config.py 注释），而 pywikibot `login()` 有 jar 即跳过重新认证——于是依赖 apihighlimits 的 500 titles/批 prop 查询会间歇 `toomanyvalues: limit is 50`（同一 jar 连跪数次、显式重新登录后秒恢复）。pywikibot 发现会话匿名时会打 `Logged in as 'IP' instead of '...'. Forcing re-login` 自愈，但可能发生在失败之后。规则：**读路径一律匿名可达**——列表查询（allpages/allimages 的 limit 参数匿名上限即 500）或 ≤50 titles/批的 prop 查询；批量存在性判断用「全量标题集内存比对」（~21 次列表请求）而非逐批 prop=info（50/批更多请求且 500/批不稳）。**写路径由两层自愈覆盖**：已缓存登录态时被踢，后续内嵌 userinfo 的响应会触发 `Logged in as 'IP' instead of '...'. Forcing re-login`；进程启动后首次取 userinfo 时已是匿名（无登录态可比对的盲区）由 fork 的 `need_right` 重登补丁兜底（见 pywikibot-update skill 的补丁清单）。两层都失败的兜底形态是响亮异常（badtoken/permission/NoUsername）→ 非零退出停机，不存在静默损坏。且互踢本身不稳定（同日 en 登录未再踢掉 zh 会话），被踢频率低于预期。
- **限速（Fandom 已接入 Cloudflare）**：`user-config.py` 必须保持 `minthrottle >= 0.25`、`put_throttle >= 2`（当前 0.25/2）。读侧：单连接全速（RTT 锁死 ~3.8 req/s）3000 请求零 429，0.25 已处拐点、再低不会更快；写侧真正瓶颈是 MediaWiki 编辑限速（user 组 40 次/分，查 `userinfo?uiprop=ratelimits`），2s → 30 次/分。失速会被 Cloudflare 429 且 `Retry-After` 高达数千秒、pywikibot 无条件睡满（`maxthrottle` 管不住）。治理方式是不触发 429（配置限速），明确不给 fork 打 `retry_after` 钳制补丁。根因考据与「何时绕开 pywikibot」见 `docs/cloudflare-429.md`。
- **批量编辑模式**（同一变换改多页）：优先 pywikibot（pagegenerators 扫描 → 本地分析出候选 → 循环 `save(bot=True)`）；裸 API 路线为备选：① 全量扫描（`list=allpages` + `prop=revisions` 取原文和 revid）→ ② 本地分析出候选清单 → ③ 循环编辑：login → csrf token → edit 带 `baserevid` 防冲突、`bot="1"` 抑制通知，写间隔 ≥1.5s（MediaWiki 编辑限速 user 组 40 次/分）。扫 28K+ 页用 `aplimit=max`（500）分批，勿逐页请求。

## MediaWiki Conversiontable

- 自定义转换规则只解析 `-{ ... }-` 块；块外的说明/HTML 不影响规则加载。规则目标（`=>` 右侧）里的 `<!--as-is-->…<!--/as-is-->` 注释对用于保护繁体目标不被 bot 译名归一——注释随转换结果透传为惰性 HTML 注释，不可见、不影响转换（2026-08-22 实测）；简体键名保持裸写，随译名任务自动更新。
- 规则键名（`=>` 左侧）不能包 `<!--as-is-->` 注释对：转换表解析器不剥注释，键名含注释的规则永不命中（2026-09-15 实测：全表 684 条裸键规则正常触发，唯一被包键名的规则不触发）。std 为模板的条目（`{{Ringa}}` 类）其别名做不了键名——裸写会被 fix:translation 归一成模板调用、包注释又不生效，两头都是死规则；这类词的简繁转换内联进模板源码解决（`-{zh-hans:…;zh-hant:…;}-`，实测在 Tooltip 参数内双向生效）。
- `//` 注释必须写在分号**前**：`foo=>bar //注释;`。若写成 `foo=>bar; //注释`，MediaWiki 按分号切段后会把注释当作下一条规则 key 的前缀，导致下一条规则静默失效（2026-08-11 在 Fandom MediaWiki 1.43.9 实测；对应核心代码 `LanguageConverter::parseCachedTable()`）。
- 排查某条规则是否生效，可用只读 API 对任意片段直接解析：`action=parse&text=<片段>&title=User:IchiSanNi/Sandbox&prop=text&contentmodel=wikitext&variant=zh-tw`；这能排除条目页缓存因素。
- 修正转换表后，新解析会立即使用新规则，但既有条目仍可能命中旧 parser cache（2026-08-11 实测：转换表 13:35 UTC 更新后任意片段已生效，而 `page_touched=12:18 UTC` 的条目仍返回旧 HTML）；对受影响的条目做 `?action=purge`（或等待缓存自然失效）。

## 验证凭据是否仍然有效

```bash
uv run python src/tools/verify_wiki_access.py
```

只读不写，同时验证 pywikibot 库和裸 API 两条路径，期望输出 `ALL CHECKS PASSED`。
验证限速配置与 pywikibot 通路健康（读 100 页 + 沙盒写一次）跑 `src/tools/test_pwb_throttle.py`，同样期望 `ALL CHECKS PASSED`。
