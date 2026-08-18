"""Discord 转发消息解析：从消息里抽长月本人推文 {tid: text}。

解析要点（2026-08-15 实证）：
- 正文位置三路全扫：content（旧式，尾部 [Link](url) 行剥除）/ embeds /
  组件树（FBK bot：type 17 容器嵌套 type 10 文本组件，递归 walk）
- 组件内正文双布局：独立组件 或 与头部同组件链接之后
- 组件消息附 "**Post Translation**" 机翻段，切除；"\\#" 转义需还原
- RT 不收：旧式 content 以 "RT @" 开头；组件式头部动词含 "reposted"
"""

import json
import re

STATUS_PAT = re.compile(r"(?:twitter|x)\.com/(\w+)/status/(\d{5,22})")


def walk(comps):
    texts = []
    for c in comps or []:
        if c.get("type") == 10 and c.get("content"):
            texts.append(c["content"])
        texts.extend(walk(c.get("components")))
    return texts


def extract(msgs):
    out = {}
    for m in msgs:
        texts = walk(m.get("components"))
        content = m.get("content", "")
        blob = content + json.dumps(m.get("embeds", [])) + "\n".join(texts)
        hits = STATUS_PAT.findall(blob)
        if not hits:
            continue
        handle, tid = hits[0]
        if handle.lower() != "nezumiironyanko":
            continue
        if content.startswith("RT @") or (texts and "reposted" in texts[0]):
            continue
        if content:
            body = re.sub(r"\n\[Link\]\([^)]*\)\s*$", "", content).strip()
        else:
            after = texts[0].split(tid, 1)[1] if tid in texts[0] else ""
            body = "\n".join([after] + texts[1:])
            body = body.split("**Post Translation**")[0].strip().replace("\\#", "#")
        if body:
            out[tid] = body
    return out
