# 一次性实证：写路径会话恢复——踢掉 zh 会话后沙盒编辑是否自愈
import sys
import time

sys.path = [
    p
    for p in sys.path
    if p and not p.replace("\\", "/").rstrip("/").endswith("GitHub/wiki-bot")
]
import pywikibot

zh = pywikibot.Site("zh", "re0")
zh.login()
print("1. zh 登录, user =", zh.user())

en = pywikibot.Site("en", "re0")
# user-config.py 故意不配 en 账号（防互踢）；本测试就是要制造互踢，运行时注入
from pywikibot import config

config.usernames["re0"]["en"] = "IchiSanNi"
en.login()  # 文档记载：en 登录会把 zh 会话服务端作废
time.sleep(2)

r = zh.simple_request(action="query", meta="userinfo", format="json").submit()
print("2. en 登录后 zh userinfo:", r["query"]["userinfo"].get("name", "(匿名)"))

p = pywikibot.Page(zh, "User:IchiSanNi/Sandbox")
p.text = f"写路径会话恢复测试 {time.strftime('%H:%M:%S')}\n"
try:
    p.save(summary="写路径会话恢复测试", bot=False, minor=False)
    print("3. 沙盒编辑成功（写路径自愈确认）")
except Exception as e:  # noqa: BLE001 诊断脚本：成功/失败都是有价值输出
    print("3. 沙盒编辑失败:", type(e).__name__, str(e)[:150])
