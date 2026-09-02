"""把指向维基百科非中文站的链接改为中文站对应条目（2026-08-18 一次性）。

依据：src/tools/audit_wikipedia_links.py 全站审计 + 各语言维基百科 langlinks
查询（lllang=zh）。仅处理当时审计出的非 zh 目标；无 zh 对应条目的
（Dawn M. Bennett / Hanakotoba / Hideaki Tezuka / Kira Buckland /
Sean Chiplock）保持原样。

用法（仓库根目录）：
    uv run python src/oneoff/fix_wikipedia_zh_links.py        # 干跑
    uv run python src/oneoff/fix_wikipedia_zh_links.py --apply
"""

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "tools"))

spec = importlib.util.spec_from_file_location(
    "audit_wikipedia_links",
    ROOT / "src" / "tools" / "audit_wikipedia_links.py",
)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

import pywikibot

# (lang, 原目标) -> zh 目标；无 zh 条目的不在此表
ZH_MAP = {
    ("en", "Aster tataricus"): "紫菀",
    ("en", "Aya Hirano"): "平野绫",
    ("en", "Conception (video game)"): "CONCEPTION 產子救世錄",
    ("en", "Erica Mendez"): "埃莉卡·文迪絲",
    ("en", "Hiroki Takahashi"): "高橋廣樹",
    ("en", "Kaede Hondo"): "本渡楓",
    ("en", "Kaiji_Tang"): "唐凯吉",
    ("en", "Kellen Goff"): "凱倫·戈夫",
    ("en", "Shatranj"): "波斯象棋",
    ("en", "Shunsuke Takeuchi"): "武内骏辅",
    ("en", "Spike Chunsoft"): "Spike Chunsoft",
    ("en", "Subaru Kimura"): "木村昴",
    ("en", "Summon Night"): "召喚夜響曲系列",
    ("en", "Toshiyuki Toyonaga"): "豐永利行",
    ("es", "Tama (gata)"): "小玉 (貓)",
}

SUMMARY = "维基百科链接改指中文站对应条目"


def replacer(lang: str, orig: str, zh: str, text: str) -> tuple[str, int]:
    """把 [[wikipedia:lang:orig|...]] 替换为 [[wikipedia:zh:zh|...]]，保留显示文本。

    语言前缀可选——en 目标实际多写作裸前缀 [[wikipedia:X]]（默认 en.wikipedia）。
    """
    pat = re.compile(
        r"\[\[wikipedia:(?:"
        + re.escape(lang)
        + r":)?"
        + re.escape(orig).replace(r"\ ", r"[ _]")
        + r"(\|[^\]]*)?\]\]"
    )
    return pat.subn(r"[[wikipedia:zh:" + zh.replace("\\", r"\\") + r"\1]]", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写入（默认干跑）")
    args = ap.parse_args()

    hits, total = audit.scan()
    print(f"pages fetched: {total}")
    # 只保留映射表覆盖的目标：页面 -> [((lang, orig), zh)]
    todo: dict[str, list[tuple[tuple[str, str], str]]] = {}
    for (lang, orig), zh in ZH_MAP.items():
        for title in sorted(hits.get(lang, {}).get(orig, ())):
            todo.setdefault(title, []).append(((lang, orig), zh))

    if args.apply:
        site = pywikibot.Site("zh", "re0")
        site.login()
        assert site.user() == "IchiSanNi"

    changed = 0
    for title, items in sorted(todo.items()):
        page = pywikibot.Page(pywikibot.Site("zh", "re0"), title)
        text = page.text
        new = text
        for (lang, orig), zh in items:
            new, n = replacer(lang, orig, zh, new)
            status = f"x{n}" if n else "未命中！"
            print(
                f"  {title}: [[wikipedia:{lang}:{orig}]] -> [[wikipedia:zh:{zh}]] {status}"
            )
        if new == text:
            continue
        changed += 1
        if args.apply:
            page.text = new
            page.save(summary=SUMMARY, bot=True)
            print(f"  已保存 {title}")
    print(f"{'已修改' if args.apply else '干跑，将修改'} {changed} 页")


if __name__ == "__main__":
    main()
