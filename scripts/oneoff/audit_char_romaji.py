"""核对所有角色页：zh 假名经 Module:Kana2Romaji 自动转换的结果 vs en 站手写 Romaji。

只读审计。输出分桶：
- MATCH        模块输出与 en 手写一致
- MISMATCH     不一致（逐条列出，用于发现模块缺漏/数据差异）
- OVERRIDE     zh 页手动指定了 name_ja_romaji（模块被绕过），另列出模块若生效会输出什么
- NO_EN        无 en 跨语言链接或 en 页无 Romaji 字段
- NO_KANA      zh 页两个假名字段都为空
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
            if method == "get":
                r = S.get(base, params=params, timeout=30)
            else:
                r = S.post(base, data=params, timeout=30)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"API failed: {base} {params}")


def batched(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def cont_params(d):
    return {k: v for k, v in d.get("continue", {}).items() if k != "continue"}


# ---------- 1. 收集 zh 角色页（前缀 + 分类双通道取并集，排除子页） ----------
titles = set()
cont = {}
while True:
    d = api(
        ZH,
        action="query",
        list="allpages",
        apprefix="角色:",
        apnamespace="0",
        aplimit="max",
        **cont,
    )
    titles.update(p["title"] for p in d["query"]["allpages"])
    if "continue" not in d:
        break
    cont = cont_params(d)
cont = {}
while True:
    d = api(
        ZH,
        action="query",
        list="categorymembers",
        cmtitle="Category:角色",
        cmnamespace="0",
        cmlimit="max",
        **cont,
    )
    titles.update(p["title"] for p in d["query"]["categorymembers"])
    if "continue" not in d:
        break
    cont = cont_params(d)
titles = sorted(t for t in titles if "/" not in t)
print(f"角色页总数: {len(titles)}")

# ---------- 2. zh wikitext：提取假名/手动罗马字字段 ----------
PARAM_RE = {
    k: re.compile(rf"^\s*\|\s*{k}\s*=\s*(.*?)\s*$", re.MULTILINE)
    for k in ("name_ja_kana", "name_ja_kanji", "name_ja_romaji")
}
zh_data = {}  # title -> dict(kana_src, kana, override)
for chunk in batched(titles, 50):
    d = api(
        ZH,
        action="query",
        prop="revisions",
        titles="|".join(chunk),
        rvprop="content",
        rvslots="main",
    )
    for p in d["query"]["pages"]:
        text = p["revisions"][0]["slots"]["main"]["content"]
        got = {}
        for k, rx in PARAM_RE.items():
            m = rx.search(text)
            got[k] = m.group(1).strip() if m else ""
        kana = got["name_ja_kana"] or got["name_ja_kanji"]
        zh_data[p["title"]] = {
            "kana": kana,
            "kana_src": "name_ja_kana" if got["name_ja_kana"] else "name_ja_kanji",
            "override": got["name_ja_romaji"],
        }
    time.sleep(0.3)

# ---------- 3. en 跨语言链接 ----------
en_title = {}  # zh title -> en title
for chunk in batched(titles, 50):
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
            en_title[p["title"]] = ll[0]["title"]
    time.sleep(0.3)

# ---------- 4. en wikitext：提取 Romaji ----------
ROMAJI_RE = re.compile(r"^\s*\|\s*Romaji\s*=\s*(.*?)\s*$", re.MULTILINE)
en_romaji = {}  # en title -> romaji
en_titles = sorted(set(en_title.values()))
for chunk in batched(en_titles, 50):
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
        m = ROMAJI_RE.search(text)
        if m:
            en_romaji[p["title"]] = m.group(1).strip()
    time.sleep(0.3)

# ---------- 5. live 模块批量转换（去重后分批 expandtemplates） ----------
kana_set = sorted({v["kana"] for v in zh_data.values() if v["kana"]})
unsafe = [k for k in kana_set if "|" in k or "}" in k or "\n" in k]
kana_safe = [k for k in kana_set if k not in unsafe]
module_out = {}
for chunk in batched(kana_safe, 20):
    text = "\n".join(f"{{{{#invoke:Kana2Romaji|Kana2Romaji|kana={k}}}}}" for k in chunk)
    d = api(ZH, method="post", action="expandtemplates", text=text, prop="wikitext")
    outs = d["expandtemplates"]["wikitext"].split("\n")
    assert len(outs) == len(chunk), (
        f"expandtemplates 对齐失败: {len(outs)} vs {len(chunk)}"
    )
    module_out.update(zip(chunk, (o.strip() for o in outs)))
    time.sleep(0.3)


# ---------- 6. 比对分桶 ----------
def norm(s):
    return re.sub(r"\s+", " ", s).strip()


match, mismatch, override_pages, no_en, no_kana = [], [], [], [], []
for t in titles:
    info = zh_data[t]
    kana = info["kana"]
    if not kana:
        no_kana.append(t)
        continue
    out = module_out.get(kana)
    et = en_title.get(t)
    er = en_romaji.get(et) if et else None
    if info["override"]:
        override_pages.append((t, kana, info["override"], out, er))
        continue
    if er is None:
        no_en.append((t, kana, out))
        continue
    if norm(out) == norm(er):
        match.append(t)
    else:
        mismatch.append((t, kana, out, er))

print(
    f"\nMATCH: {len(match)}  MISMATCH: {len(mismatch)}  "
    f"OVERRIDE: {len(override_pages)}  NO_EN: {len(no_en)}  NO_KANA: {len(no_kana)}"
)
if unsafe:
    print(f"跳过不安全假名值: {unsafe}")

print("\n===== MISMATCH（页面 | 假名 | 模块输出 | en 手写） =====")
for t, kana, out, er in mismatch:
    print(f"{t} | {kana} | {out} | {er}")

print("\n===== OVERRIDE（页面 | 假名 | zh 手动值 | 模块会输出 | en 手写） =====")
for t, kana, ov, out, er in override_pages:
    print(f"{t} | {kana} | {ov} | {out} | {er}")

print("\n===== NO_EN（页面 | 假名 | 模块输出） =====")
for t, kana, out in no_en:
    print(f"{t} | {kana} | {out}")

print("\n===== NO_KANA =====")
for t in no_kana:
    print(t)

with open("logs/audit_char_romaji.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "match": match,
            "mismatch": [list(x) for x in mismatch],
            "override": [list(x) for x in override_pages],
            "no_en": [list(x) for x in no_en],
            "no_kana": no_kana,
        },
        f,
        ensure_ascii=False,
        indent=1,
    )
