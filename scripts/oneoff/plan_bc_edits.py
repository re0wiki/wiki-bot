"""生成 B（假名同步 en Kanji）与 C（清除无汉字 override）编辑计划。只读。

判定规则：
- 分隔符归一：en 的 ・ → zh 的 ·；<br> 前后空白归一。
- 注记（(...) 与（...）内容，如 (current)/(former)/（舊名）/(Web)）在比对时剥离，编辑时保留 zh 侧注记。
- B：zh 活动假名字段（name_ja_kana 优先，否则 name_ja_kanji）逐行与 en Kanji 比对，
  en 的每一行归一后都应能在 zh 行中找到；找不到 → 该行需更新/补充。
- C：name_ja_romaji 非空 且 假名（B 更新后）剥离注记后不含汉字 → 清除 override。
- 汉字检测：CJK 统一表意文字。含汉字的页保留/新增 override（另列清单人工确认）。
"""

import json
import re
import time
from difflib import SequenceMatcher

import requests

ZH = "https://rezero.fandom.com/zh/api.php"
EN = "https://rezero.fandom.com/api.php"
S = requests.Session()

CJK = re.compile(r"[一-鿿㐀-䶿]")
ANNOT = re.compile(r"\([^()]*\)|（[^（）]*）")


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


def cont_params(d):
    return {k: v for k, v in d.get("continue", {}).items() if k != "continue"}


def norm_sep(s):
    return s.replace("・", "·")


def strip_annot(s):
    return ANNOT.sub("", s)


def norm_line(s):
    return re.sub(r"\s+", " ", norm_sep(strip_annot(s))).strip(" ·")


def split_lines(s):
    return [x.strip() for x in re.split(r"<br\s*/?>", s) if x.strip()]


def has_kanji(s):
    return bool(CJK.search(strip_annot(s)))


# ---------- 收集页面 ----------
titles = set()
for src, kw in (
    ("allpages", {"apprefix": "角色:", "apnamespace": "0", "aplimit": "max"}),
    (
        "categorymembers",
        {"cmtitle": "Category:角色", "cmnamespace": "0", "cmlimit": "max"},
    ),
):
    cont = {}
    while True:
        d = api(ZH, action="query", list=src, **kw, **cont)
        key = "allpages" if src == "allpages" else "categorymembers"
        titles.update(p["title"] for p in d["query"][key])
        if "continue" not in d:
            break
        cont = cont_params(d)
titles = sorted(t for t in titles if "/" not in t)

PARAM_RE = {
    k: re.compile(
        rf"^([ \t]*\|[ \t]*{k}[ \t]*=[ \t]*)([^\n]*?)[ \t]*\r?$", re.MULTILINE
    )
    for k in ("name_ja_kana", "name_ja_kanji", "name_ja_romaji")
}

pages = {}
for chunk in batched(titles, 50):
    d = api(
        ZH,
        action="query",
        prop="revisions|langlinks",
        titles="|".join(chunk),
        rvprop="content",
        rvslots="main",
        lllang="en",
        lllimit="max",
    )
    for p in d["query"]["pages"]:
        text = p["revisions"][0]["slots"]["main"]["content"]
        got = {}
        for k, rx in PARAM_RE.items():
            m = rx.search(text)
            got[k] = m.group(2) if m else None
        ll = p.get("langlinks")
        pages[p["title"]] = {
            "kana": got["name_ja_kana"],
            "kanji_f": got["name_ja_kanji"],
            "override": got["name_ja_romaji"],
            "en": ll[0]["title"] if ll else None,
        }
    time.sleep(0.3)

# ---------- en Kanji ----------
en_kanji = {}
en_titles = sorted({v["en"] for v in pages.values() if v["en"]})
KANJI_RE = re.compile(r"^\s*\|\s*Kanji\s*=\s*([^\n|]*?)\s*\r?$", re.MULTILINE)
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
        m = KANJI_RE.search(text)
        en_kanji[p["title"]] = m.group(1) if m else ""
    time.sleep(0.3)

# ---------- 计划 ----------
b_edits, c_removes, keep_override, notes = [], [], [], []
for t, v in sorted(pages.items()):
    active_field = "kana" if v["kana"] else "kanji_f"
    cur = v[active_field] or ""
    override = (v["override"] or "").strip()
    ek = en_kanji.get(v["en"]) if v["en"] else None

    # --- B：假名同步 ---
    new_cur = None
    if ek:
        zh_lines = split_lines(cur)
        en_lines = split_lines(ek)
        zh_norm = [norm_line(x) for x in zh_lines]
        en_norm = [norm_line(x) for x in en_lines]
        if not cur and en_lines:
            # zh 假名空、en 有 → 补全（如 馬達拉）；汉字名不补（字段语义不符，归 D）
            cand = "<br>".join(norm_sep(strip_annot(x)).strip() for x in en_lines)
            if has_kanji(cand):
                notes.append(f"B跳过(汉字名) {t}: en={cand}")
            else:
                new_cur = cand
                notes.append(f"B补全 {t}: (空) -> {new_cur}")
        elif zh_lines:
            merged = list(zh_lines)
            diffs = []
            if len(zh_lines) == 1 and len(en_lines) > 1:
                # en 合并页（多行）：zh 单行精确命中某行 → 不动；否则取最相似行
                if zh_norm[0] in en_norm:
                    pass
                else:
                    best = max(
                        range(len(en_norm)),
                        key=lambda j: SequenceMatcher(
                            None, zh_norm[0], en_norm[j]
                        ).ratio(),
                    )
                    ratio = SequenceMatcher(None, zh_norm[0], en_norm[best]).ratio()
                    if ratio >= 0.6 and not has_kanji(en_norm[best]):
                        diffs.append((zh_lines[0], en_lines[best]))
                        merged[0] = norm_sep(strip_annot(en_lines[best])).strip()
                    else:
                        notes.append(
                            f"B跳过(无相似行) {t}: {zh_lines[0]} vs en={en_lines}"
                        )
            else:
                # 逐行对：en 第 i 行应与 zh 第 i 行一致（zh 多出的别名行保留；en 多出的行不补——避免合并页串行）
                for i, en_l in enumerate(en_norm[: len(zh_norm)]):
                    if zh_norm[i] != en_l:
                        cand = norm_sep(strip_annot(en_lines[i])).strip()
                        if has_kanji(cand):
                            notes.append(
                                f"B跳过(汉字名) {t}: {zh_lines[i]} vs en={en_lines[i]}"
                            )
                            continue
                        diffs.append((zh_lines[i], en_lines[i]))
                        # 保留 zh 注记：用 en 的名字部分 + zh 的注记
                        annot = "".join(ANNOT.findall(zh_lines[i]))
                        merged[i] = cand + (f"({annot})" if annot else "")
            if diffs:
                new_cur = "<br>".join(merged)
                for old_l, new_l in diffs:
                    notes.append(f"B更新 {t}: {old_l} -> {new_l}")

    cur_after = new_cur if new_cur is not None else cur
    if new_cur is not None:
        b_edits.append(
            {
                "title": t,
                "field": "name_ja_kana" if active_field == "kana" else "name_ja_kanji",
                "old": cur,
                "new": new_cur,
            }
        )

    # --- C：override 清理 ---
    if override:
        if has_kanji(cur_after):
            keep_override.append((t, cur_after, override))
        else:
            c_removes.append({"title": t, "override": override})

# 汉字页但无 override（需新增 override，人工确认值）
kanji_no_override = [
    (t, (v["kana"] or v["kanji_f"] or ""))
    for t, v in sorted(pages.items())
    if has_kanji(v["kana"] or v["kanji_f"] or "") and not (v["override"] or "").strip()
]

plan = {
    "b_edits": b_edits,
    "c_removes": c_removes,
    "keep_override": keep_override,
    "kanji_no_override": kanji_no_override,
}
with open("logs/bc_plan.json", "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=1)

print(
    f"B 编辑: {len(b_edits)}  C 清除: {len(c_removes)}  保留 override(汉字): {len(keep_override)}  汉字无 override: {len(kanji_no_override)}"
)
print("\n--- B 明细 ---")
for n in notes:
    print(n)
print("\n--- 保留 override（汉字页） ---")
for t, k, o in keep_override:
    print(f"{t} | {k} | {o}")
print("\n--- 汉字无 override（需新增） ---")
for t, k in kanji_no_override:
    print(f"{t} | {k}")
print("\n--- C 清除抽样（前 15） ---")
for c in c_removes[:15]:
    print(f"{c['title']} | 清除: {c['override']}")
