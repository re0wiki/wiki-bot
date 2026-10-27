"""部署：变更月表 + 新非空月表 /doc 补骨架 + 主模块同步（全部对 lua_live 快照差量）。"""

import sys
import time

import pywikibot
from pywikibot.exceptions import EditConflictError

from . import DATA


def same_wiki_text(left: str, right: str) -> bool:
    """MediaWiki 会剥文件尾换行；内容比较忽略这一表示差异。"""
    return left.rstrip("\n") == right.rstrip("\n")


def save_guarded(page, *, summary: str, createonly: bool = False) -> None:
    """既有页绑定已读 revid；新页禁止覆盖检查后并发创建的内容。"""
    kwargs = {"summary": summary, "bot": True}
    if createonly:
        kwargs["createonly"] = True
    else:
        kwargs["baserevid"] = page.latest_revision.revid
    page.save(**kwargs)


def _sync_main_module(site) -> bool:
    # 主模块重生成（data_names 已程序化，直接推 emit 产物）
    main_src = (DATA / "main.lua").read_text(encoding="utf-8")
    p = pywikibot.Page(site, "Module:NekoQuote")
    if same_wiki_text(p.text, main_src):
        return True
    main_exists = p.exists()
    p.text = main_src
    try:
        save_guarded(p, summary="语录主模块同步", createonly=not main_exists)
    except EditConflictError:
        print("主模块保存冲突；线上已变化，未覆盖，中止", flush=True)
        return False
    return True


def _changed_months() -> list[str]:
    # 变更月表 = emit 与上次部署快照（lua_live）不一致的
    changed = []
    for f in sorted((DATA / "lua").glob("*.lua")):
        live = DATA / "lua_live" / f.name
        if not live.exists() or not same_wiki_text(
            live.read_text(encoding="utf-8"), f.read_text(encoding="utf-8")
        ):
            changed.append(f.stem)
    return changed


def _deploy_month(site, month: str) -> bool:
    content = (DATA / "lua" / f"{month}.lua").read_text(encoding="utf-8")
    live = DATA / "lua_live" / f"{month}.lua"
    p = pywikibot.Page(site, f"Module:NekoQuote/{month}")
    online = p.text
    needs_save = not same_wiki_text(online, content)
    createonly = False
    if not needs_save:
        # 快照滞后导致的「假变更」：内容已与线上一致，省一次写请求；
        # /doc 仍需检查，覆盖上次月表成功而 /doc 失败的重试。
        print(f"  {month} ≡（与线上一致，仅快照滞后）", flush=True)
    else:
        if live.exists():
            baseline = live.read_text(encoding="utf-8")
            if not same_wiki_text(online, baseline):
                print(
                    f"  {month} 线上内容与上次部署快照不一致；先运行 pull_wiki 合并，中止",
                    flush=True,
                )
                return False
        elif p.exists():
            print(
                f"  {month} 线上页面已存在但无部署基线；人工核对后再部署，中止",
                flush=True,
            )
            return False
        else:
            createonly = True
        p.text = content
        t0 = time.perf_counter()
        try:
            save_guarded(p, summary="语录月表增量更新", createonly=createonly)
        except EditConflictError:
            print(f"  {month} 保存冲突；线上已变化，未覆盖，中止", flush=True)
            return False
        print(f"  {month} ✓ ({time.perf_counter() - t0:.1f}s)", flush=True)
    return True


def _deploy_doc(site, month: str) -> bool:
    # /doc：新非空月表补骨架（统一 Template:NekoQuoteDoc）；每次变更都幂等检查。
    d = pywikibot.Page(site, f"Module:NekoQuote/{month}/doc")
    if "{{NekoQuoteDoc}}" in d.text:
        return True
    doc_exists = d.exists()
    d.text = "{{NekoQuoteDoc}}"
    try:
        save_guarded(d, summary="语录 /doc 骨架", createonly=not doc_exists)
    except EditConflictError:
        print(f"  {month}/doc 保存冲突；线上已变化，未覆盖，中止", flush=True)
        return False
    return True


def main() -> int:
    site = pywikibot.Site("zh", "re0")
    site.login()
    assert site.user() == "IchiSanNi"

    if not _sync_main_module(site):
        return 1
    print("主模块 ✓")

    changed = _changed_months()
    print(f"变更月表 {len(changed)} 张（vs 上次部署）")

    for month in changed:
        if not _deploy_month(site, month):
            return 1
        if not _deploy_doc(site, month):
            return 1
    print("完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
