"""把 en 主空间有、zh 主空间没有的页面批量搬运到 zh（高效版 transferbot）。

pywikibot 自带 transferbot（-lang:en -tolang:zh -start）逐页迭代 en 主空间
并逐页 targetpage.exists() 单独查询，~2500-4000 请求/轮、15-16 分钟
（2026-08-13 实测，见 docs/todo.md）。本脚本：
1. en/zh 主空间标题集各 500/批拉取（~30 请求）内存比对出缺失页；
2. 缺失页的 en 内容 50/批取回，按 fork 补丁同款格式加页首
   （{{Init}}{{To do}} + 来源链接 + [[Category:新搬运待整理]]）后创建；
3. 创建前对缺失清单做一次 zh 侧批量复核，防比对间隙的竞争。

与原任务的边界一致：只覆盖 ns 0（原 -start 即主空间，fork 的 ns 8/828
排除分支用不到）；en 重定向不搬（原生成器不含重定向）；zh 同名重定向
视为已存在（原 exists() 语义）。
"""

import pywikibot as pwb
from pywikibot import config
from pywikibot.tools import first_upper

HEADER = "{{Init}}\n{{To do}}\n"
FOOTER_CATEGORY = "\n[[Category:新搬运待整理]]"


def normalize(title: str) -> str:
    """归一到 MediaWiki 规范标题（下划线转空格、首字母大写）。"""
    return first_upper(title.replace("_", " ").strip())


def build_text(en_text: str, title: str) -> str:
    """fork 补丁同款：页首 {{Init}}{{To do}} + 原文 + 来源链接 + 待整理分类。"""
    return f"{HEADER}{en_text}\n[[en:{title}]]{FOOTER_CATEGORY}"


def build_summary(title: str) -> str:
    """fork 补丁同款摘要（i18n transferbot-summary 的 zh 文案）。"""
    return f"自[[en:{title}]]搬运页面"


if __name__ == "__main__":
    pwb.handle_args()  # -always 等忽略：不询问；-s 走下方分支
    en = pwb.Site("en", "re0")
    zh = pwb.Site()
    en_titles = {
        normalize(p.title()) for p in en.allpages(namespace=0, filterredir=False)
    }
    zh_titles = {normalize(p.title()) for p in zh.allpages(namespace=0)}
    missing = sorted(en_titles - zh_titles)
    pwb.info(f"en {len(en_titles)} 页，zh {len(zh_titles)} 页，缺失 {len(missing)} 页")
    if missing:
        # 竞争防护：创建前 zh 侧批量复核（通常 1 次请求）
        recheck = [
            p["title"]
            for i in range(0, len(missing), 50)
            for p in zh.simple_request(
                action="query",
                prop="info",
                titles="|".join(missing[i : i + 50]),
                formatversion="2",
                format="json",
            ).submit()["query"]["pages"]
            if p.get("missing")
        ]
        # 批量取 en 内容（50/批）
        for i in range(0, len(recheck), 50):
            data = en.simple_request(
                action="query",
                prop="revisions",
                rvprop="content",
                rvslots="main",
                titles="|".join(recheck[i : i + 50]),
                formatversion="2",
                format="json",
            ).submit()
            for p in data["query"]["pages"]:
                title = p["title"]
                if "missing" in p:
                    pwb.warning(f"en 页 {title} 不存在（比对间隙被删？），跳过")
                    continue
                if config.simulate:
                    pwb.info(f"将搬运 {title}")
                    continue
                page = pwb.Page(zh, title)
                page.text = build_text(
                    p["revisions"][0]["slots"]["main"]["content"], title
                )
                page.save(summary=build_summary(title), bot=True)
                pwb.info(f"已搬运 {title}")
