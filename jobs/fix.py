from .jobs_ import CmdJob, add_job

fixes = [
    # built-in fixes
    "HTML",
    "syntax",
    "isbn",
    "specialpages",
    # user-fixes.py
    "misc",
    # "args",
    "gallery",
    "head",
    "translation",
]

for fix in sorted(fixes):
    add_job(CmdJob(["replace", "-automaticsummary", "-always", "-fix:" + fix]))
