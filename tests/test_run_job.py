"""jobs/run_job.py 命令行拼装的纯函数测试（不触 wiki、不起子进程）。"""

import sys

from repo_loader import load_module

rj = load_module("run_job", "jobs/run_job.py")


def test_cmd_uses_current_interpreter():
    """必须用 sys.executable：裸 "python" 从 PATH 解析，可能跑错版本。"""
    cmd = rj.build_cmd(["touch"])
    assert cmd[0] == sys.executable
    assert cmd[1] == "pywikibot/pwb.py"
    assert cmd[2] == "touch"


def test_normal_job_gets_always():
    assert rj.build_cmd(["replace", "-fix:misc"])[-1] == "-always"


def test_simulate_replaces_always():
    cmd = rj.build_cmd(["replace", "-fix:misc"], simulate=True)
    assert cmd[-1] == "-simulate"
    assert "-always" not in cmd


def test_interwiki_gets_auto_force():
    cmd = rj.build_cmd(["interwiki", "-quiet"])
    assert cmd[-2:] == ["-auto", "-force"]


def test_interwiki_simulate_takes_precedence():
    cmd = rj.build_cmd(["interwiki", "-quiet"], simulate=True)
    assert cmd[-1] == "-simulate"
    assert "-auto" not in cmd


def test_transferbot_rejects_always():
    """transferbot 不接受 -always（加了会报错），且不加也会自动覆盖目标页。"""
    cmd = rj.build_cmd(["transferbot", "-lang:en"])
    assert "-always" not in cmd
