"""从 wiki 重建语录本地基线——新 clone 首次运行时的自愈入口。

wiki 月表是唯一权威副本；lua_base 缺失时把全部月表拉回本地（含已合流的
raw 推文条目——tweets.json 从空起步，既有条目的推 id 都在 src 里，
构建期的 id 级去重保证不会重复收录；增量链从空 tweets.json
起步即可正确工作）。抓取先在临时目录完成；发布时保留旧版本备份，任一步失败
都回滚，只有两张目录均发布成功才写完成标记。异常退出留下的备份会在下次运行
先恢复或清理。
"""

import shutil
from datetime import UTC, datetime

import pywikibot

from . import DATA
from .state import state_lock, write_json

BASE = DATA / "lua_base"
COMPLETE = DATA / "lua_base.complete"


def needed() -> bool:
    return not COMPLETE.exists()


def _targets() -> tuple:
    return BASE, DATA / "lua_live"


def _backup(target):
    return target.with_name(target.name + ".backup")


def _recover_or_cleanup() -> None:
    """完成标记在 = 已提交，清旧备份；不在 = 未提交，恢复旧目录。"""
    if COMPLETE.exists():
        for target in _targets():
            shutil.rmtree(_backup(target), ignore_errors=True)
        return
    for target in _targets():
        backup = _backup(target)
        if backup.exists():
            if target.exists():
                shutil.rmtree(target)
            backup.rename(target)


def _publish(base_stage, live_stage) -> None:
    """成对发布 base/live；目录或完成标记任一步失败均恢复旧完整版本。"""
    had_complete = COMPLETE.exists()
    backups = []
    published = []
    COMPLETE.unlink(missing_ok=True)
    try:
        for target, stage in ((BASE, base_stage), (DATA / "lua_live", live_stage)):
            backup = _backup(target)
            if backup.exists():
                shutil.rmtree(backup)
            if target.exists():
                target.rename(backup)
                backups.append((target, backup))
            stage.rename(target)
            published.append(target)
        write_json(COMPLETE, {})
    except Exception:
        for target in reversed(published):
            shutil.rmtree(target, ignore_errors=True)
        for target, backup in reversed(backups):
            if backup.exists():
                backup.rename(target)
        if had_complete:
            # 标记恢复不走可能正是故障源的 write_json。
            COMPLETE.touch(exist_ok=True)
        raise
    for _, backup in backups:
        shutil.rmtree(backup, ignore_errors=True)


def run() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    _recover_or_cleanup()
    base_stage = DATA / "lua_base.staging"
    live_stage = DATA / "lua_live.staging"
    for stage in (base_stage, live_stage):
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)

    site = pywikibot.Site("zh", "re0")  # 只读，无需登录
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
                (base_stage / f"{name}.lua").write_text(text, encoding="utf-8")
                (live_stage / f"{name}.lua").write_text(text, encoding="utf-8")
                n += 1
    for name in ("tweets.json", "zh.json", "ep_marks.json"):
        f = DATA / name
        if not f.exists():
            write_json(f, {})

    _publish(base_stage, live_stage)
    print(f"bootstrap：从 wiki 重建 {n} 张月表基线 ✓")


def main() -> None:
    with state_lock(DATA):
        run()


if __name__ == "__main__":
    main()
