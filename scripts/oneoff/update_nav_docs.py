"""一次性：User:IchiSanNi/jobs 移除「编译导航栏」任务条目（已换装为 Module 实时编译）。"""

import pywikibot

site = pywikibot.Site("zh", "re0")
site.login()
assert site.user() == "IchiSanNi"

jobs = pywikibot.Page(site, "User:IchiSanNi/jobs")
old = "* '''编译导航栏'''：将 [[Project:Wiki-navigation]] 的内容编译至 [[MediaWiki:Wiki-navigation]]。\n"
assert old in jobs.text, "jobs 页条目与预期不符"
jobs.text = jobs.text.replace(old, "", 1)
jobs.save(
    summary="移除「编译导航栏」：已换装为 Module:Wiki-navigation 实时编译",
    bot=False,
    minor=False,
)
print("jobs page updated")
