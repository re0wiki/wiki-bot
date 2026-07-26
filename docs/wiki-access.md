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
p.save(summary="编辑摘要")            # 手动编辑特定页面：不加 bot flag
p.save(summary="编辑摘要", bot=True)  # 批量脚本：加 bot=True（或 p.put(...)）
```

- **bot flag 的取舍**：bot flag 会阻止常规通知机制（避免批量编辑刷屏）。跑批量脚本时用 `bot=True` 没问题；但手动编辑特定页面时，操作更接近需人工审查的常规编辑，**不要加 bot flag**。
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
```

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

对照表：MediaWiki API action ↔ pywikibot 方法见 `pywikibot/docs/mwapi.rst`。

## 裸 requests + BotPassword（逃生舱的逃生舱，一般不推荐）

优先库方式；simple_request 也解决不了的，再裸调 `https://rezero.fandom.com/zh/api.php`。
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
（token=csrf, bot="1"）。**login token 和 csrf token 必须分两次取**（Fandom 一起取会缺 token）。
加 `formatversion=2` 可让响应没有数字键，解析更干净。完整可跑代码见 `scripts/verify_wiki_access.py`。
**login POST 也必须走带 429 退避的重试封装**，不能裸发——否则一被限速连登录都过不去（实测踩过）。

## 实测结论与坑

- 搜索"菜月昴"能命中 `角色:菜月·昴` 等页（Fandom 搜索对别名友好），但 `intitle:` 语法无效；`insource:` 也不支持（`site.search('insource:"Init"')` 返回 0 但字符串其实遍地都是）。信任任何搜索语法前先用已知真/已知假查询 sanity check。
- Fandom API **不支持** `list=mostlinkedtemplates`；查模板引用量改用 `Page.embeddedin(total=N)` 逐个查。
- `api.QueryGenerator` 带 `generator=` 时**逐页 yield page dict**（不是 `{"query": {"pages": {...}}}` 包裹结构）；不带 generator 时才是整包响应。解析前先确认用的是哪种形态。
- `allcategories` 不支持 `acsort` 参数，返回条目也没有 `size` 键；分类规模用 `Category.categoryinfo`。
- `site.namespaces` 迭代返回的是 int 键，取对象用 `site.namespaces[ns_id]`。
- `Page.getVersionHistory()` 在 11.x 不存在；最新版本用 `page.latest_revision`，最早版本用裸 API（`rvdir=newer, rvlimit=1`）。
- `Page.isRedirectPage()` 对 `#重定向 [[...]]` 的页面可能误报 `False`——信 wikitext 不信标志位。
- **`embeddedin`/templatelinks = 0 不等于没人用**：`#tag:` 扩展内容和死模板 `<includeonly>` 里的调用不入 templatelinks。模板删除前审计流程（全站 dump 配方、分类法、删除清单）见 `docs/template-usage-audit.md`。
- `RecentChangesPageGenerator` 返回有重复条目（同一编辑出现多次），统计时需去重。
- 主空间 `allpages` 按字母序，CJK 前缀排在英文之后——采样统计前缀分布必须扫全量。
- 写沙盒后可用 `curl 'https://rezero.fandom.com/zh/api.php?action=query&prop=revisions&titles=...&rvprop=content&rvslots=main&format=json'` 匿名验证结果。
- **限速（Fandom 已接入 Cloudflare）**：`user-config.py` 必须保持 `minthrottle >= 1`、`put_throttle >= 5`（当前 1/5，实测全任务零 429）。失速会被 Cloudflare 429 且 `Retry-After` 高达数千秒、pywikibot 无条件睡满（`maxthrottle` 管不住）。治理方式是不触发 429（配置限速），明确不给 fork 打 `retry_after` 钳制补丁。根因考据与「何时绕开 pywikibot」见 `docs/cloudflare-429.md`。
- **批量编辑模式**（同一变换改多页）：优先 pywikibot（pagegenerators 扫描 → 本地分析出候选 → 循环 `save(bot=True)`）；裸 API 路线为备选：① 全量扫描（`list=allpages` + `prop=revisions` 取原文和 revid）→ ② 本地分析出候选清单 → ③ 循环编辑：login → csrf token → edit 带 `baserevid` 防冲突、`bot="1"` 抑制通知，写间隔 ≥0.5s。扫 28K+ 页用 `aplimit=max`（500）分批，勿逐页请求。

## 验证凭据是否仍然有效

```bash
PYTHONPATH= .venv/Scripts/python.exe scripts/verify_wiki_access.py
```

只读不写，同时验证 pywikibot 库和裸 API 两条路径，期望输出 `ALL CHECKS PASSED`。
验证限速配置与 pywikibot 通路健康（读 100 页 + 沙盒写一次）跑 `scripts/test_pwb_throttle.py`，同样期望 `ALL CHECKS PASSED`。
