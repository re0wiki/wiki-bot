# 一次性探测：allimages aiprop=timestamp 的响应结构 + imageinfo 批量结构
import requests

h = {"User-Agent": "IchiSanNi/debug (https://rezero.fandom.com/wiki/User:IchiSanNi)"}
r = requests.get(
    "https://rezero.fandom.com/zh/api.php",
    params={"action": "query", "list": "allimages", "aiprop": "timestamp", "ailimit": "3", "format": "json", "formatversion": "2"},
    headers=h,
    timeout=15,
).json()
print("allimages sample:", r["query"]["allimages"])
