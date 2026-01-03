from .jobs_ import Job, add_job

fixes = [  # built-in fixes
    "HTML",
    "syntax",
    "isbn",
    "specialpages",
] + [  # user-fixes.py
    "misc",
    "date",
    "para",
    "gallery",
    "heading",
    "translation",
    "anti-ve",
]

for fix in sorted(fixes):
    add_job(Job(["replace", "-automaticsummary", "-always", "-fix:" + fix]))
