"""从 wiki 重建语录本地基线——新 clone 首次运行时的自愈入口。

wiki 月表是唯一权威副本；lua_base 缺失时把全部月表拉回本地（含已合流的
raw 推文条目——tweets.json 从空起步，既有条目的推 id 都在 src 里，
构建期的 id 级去重保证不会重复收录；FBK 只转发新推，增量链从空 tweets.json
起步即可正确工作）。
"""

from datetime import UTC, datetime

import pywikibot

from . import DATA

BASE = DATA / "lua_base"


def needed() -> bool:
    return not (BASE.exists() and any(BASE.glob("*.lua")))


def run() -> None:
    site = pywikibot.Site("zh", "re0")  # 只读，无需登录
    BASE.mkdir(parents=True, exist_ok=True)
    live = DATA / "lua_live"
    live.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    n = 0
    for y in range(2010, now.year + 1):
        for m in range(1, 13):
            if (y, m) > (now.year, now.month):
                break
            name = f"{y}-{m:02d}"
            p = pywikibot.Page(site, f"Module:NekoQuote/{name}")
            if p.exists():
                # MediaWiki 剥文件尾换行，构建器 emit 有——对齐到构建器约定，
                # 保证 lua_live 与首建产物逐字节一致（首跑零变更部署）
                text = p.text if p.text.endswith("\n") else p.text + "\n"
                (BASE / f"{name}.lua").write_text(text, encoding="utf-8")
                (live / f"{name}.lua").write_text(text, encoding="utf-8")
                n += 1
    for name in ("tweets.json", "zh.json", "ep_marks.json"):
        f = DATA / name
        if not f.exists():
            f.write_text("{}", encoding="utf-8")
    print(f"bootstrap：从 wiki 重建 {n} 张月表基线 ✓")


if __name__ == "__main__":
    run()
