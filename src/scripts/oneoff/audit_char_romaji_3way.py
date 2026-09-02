"""三方比对（第二轮）：en 站 Kanji 字段经模块转换 vs en 手写 Romaji，判断 en 是否自洽。

输入：logs/audit_char_romaji.json（第一轮结果）。
输出：
- EN_SELF_CONSISTENT: 模块(en Kanji) == en Romaji → 差异在 zh 假名数据
- EN_DEVIATES:       模块(en Kanji) != en Romaji → en 自身偏离模块的平文式
另附 en Subaru 页 Romaji 行原文核查。
"""

import json
import re
import time

import requests

ZH = "https://rezero.fandom.com/zh/api.php"
EN = "https://rezero.fandom.com/api.php"
S = requests.Session()


def api(base, method="get", **params):
    params.update(format="json", formatversion="2")
    for attempt in range(5):
        try:
            r = (
                S.get(base, params=params, timeout=30)
                if method == "get"
                else S.post(base, data=params, timeout=30)
            )
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"API failed: {base}")


def batched(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


with open("logs/audit_char_romaji.json", encoding="utf-8") as f:
    d1 = json.load(f)

# 需要核查的页面：MISMATCH 全部 + OVERRIDE 中三方不一致的
targets = {}  # zh title -> (kana, module_out, en_romaji)
for t, kana, out, er in d1["mismatch"]:
    targets[t] = (kana, out, er)
for t, kana, ov, out, er in d1["override"]:
    if er and norm(out) != norm(er):
        targets[t] = (kana, out, er)

# zh -> en 标题
zh_titles = sorted(targets)
en_of = {}
for chunk in batched(zh_titles, 50):
    d = api(
        ZH,
        action="query",
        prop="langlinks",
        titles="|".join(chunk),
        lllang="en",
        lllimit="max",
    )
    for p in d["query"]["pages"]:
        ll = p.get("langlinks")
        if ll:
            en_of[p["title"]] = ll[0]["title"]
    time.sleep(0.3)

# en Kanji + Romaji 行原文
FIELD_RE = {
    k: re.compile(rf"^\s*\|\s*{k}\s*=\s*(.*?)\s*$", re.MULTILINE)
    for k in ("Kanji", "Romaji")
}
en_data = {}
for chunk in batched(sorted(set(en_of.values())), 50):
    d = api(
        EN,
        action="query",
        prop="revisions",
        titles="|".join(chunk),
        rvprop="content",
        rvslots="main",
    )
    for p in d["query"]["pages"]:
        if "missing" in p:
            continue
        text = p["revisions"][0]["slots"]["main"]["content"]
        en_data[p["title"]] = {
            k: (m.group(1).strip() if (m := rx.search(text)) else "")
            for k, rx in FIELD_RE.items()
        }
    time.sleep(0.3)

# 模块转换 en Kanji
kanji_set = sorted({v["Kanji"] for v in en_data.values() if v["Kanji"]})
kanji_safe = [k for k in kanji_set if "|" not in k and "}" not in k and "\n" not in k]
mod = {}
for chunk in batched(kanji_safe, 20):
    text = "\n".join(f"{{{{#invoke:Kana2Romaji|Kana2Romaji|kana={k}}}}}" for k in chunk)
    d = api(ZH, method="post", action="expandtemplates", text=text, prop="wikitext")
    outs = d["expandtemplates"]["wikitext"].split("\n")
    assert len(outs) == len(chunk)
    mod.update(zip(chunk, (o.strip() for o in outs)))
    time.sleep(0.3)

print(
    "zh 页面 | zh 假名 | 模块(zh假名) | en Kanji | 模块(en Kanji) | en Romaji | 判定\n"
)
rows = []
for t in zh_titles:
    kana, out, er = targets[t]
    et = en_of.get(t)
    ed = en_data.get(et, {})
    ek, mo = ed.get("Kanji", ""), mod.get(ed.get("Kanji", ""), "")
    if not et or not ed:
        verdict = "EN_PAGE?"
    elif not ek:
        verdict = "NO_EN_KANJI"
    elif norm(mo) == norm(er):
        verdict = "EN自洽→zh假名不同步"
    elif norm(out) == norm(er):
        verdict = "zh假名自洽→en不同步"
    else:
        verdict = "en偏离模块规则"
    rows.append((t, kana, out, ek, mo, er, verdict))
    print(" | ".join(str(x or "") for x in (t, kana, out, ek, mo, er, verdict)))

with open("logs/audit_char_romaji_3way.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
