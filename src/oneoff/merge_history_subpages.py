"""一次性迁移：译自 en History 的 角色:/梗概 子页并回主页面 == 经历 == 章节。

背景：zh 曾把角色生平拆到 /经历（后 /梗概）子页；en 对多数角色把生平放在
主页面 ==History== 章节（/Synopsis 子页是另一粒度的逐章剧情）。zh 子页无 en
对应 → LLM 管线打 revid - 标记视为 zh 原创、退出自动更新。本脚本对「en 无
/Synopsis 且主页面有 History」的 15 个角色执行：子页正文剥页首页尾、标题
降一级，并入主页面 == 经历 == 章节，随后删除子页。

- 非译自 en History 的子页（璞可/沃尔夫，zh 原创游戏剧情）不动；
- en 有 /Synopsis 的 10 个角色与全部作品页不动；
- 子页删除后产生的破损重定向由循环任务 redirect-br 自动清理，不特别处理。

用法: uv run python src/oneoff/merge_history_subpages.py [-s] [标题过滤子串]
"""

import re
import sys

import pywikibot

SIMULATE = "-s" in sys.argv
FILTER = next((a for a in sys.argv[1:] if not a.startswith("-")), None)

# 2026-09-23 全站调查确立的 15 个合并对象（en 无 /Synopsis、主页面有 History）。
# 运行时逐个 revalidate，状态不符即跳过。
TARGETS = [
    "角色:傅里叶·卢克尼卡",
    "角色:卡罗尔·莱蒙蒂斯",
    "角色:培提奇乌斯·罗曼尼康帝",
    "角色:塞西鲁斯·塞格蒙德",
    "角色:威尔海姆·梵·阿斯特雷亚",
    "角色:文森特·佛拉基亚",
    "角色:斯特莱德·佛拉基亚",
    "角色:格林·法先",
    "角色:梅尔蒂·布里司堤斯",
    "角色:汉娜·丽格蕾特",
    "角色:莱因哈鲁特·梵·阿斯特雷亚",
    "角色:菲莉丝",
    "角色:萨尔姆·布里司堤斯",
    "角色:阿尔迪巴兰",
    "角色:鲁伊·阿内芙",
]

EN_LINK = re.compile(r"\[\[en:([^\]|]+)", re.IGNORECASE)
LLM_MARK = re.compile(r"<!--\s*(?:LLM|K3):[^>]*-->\n?")
HIST_EN = re.compile(r"^==\s*History\s*==\s*$", re.MULTILINE | re.IGNORECASE)
# 主页面已有的历史类章节（normalize_history_headings.py 已跑时只剩「经历」）
HIST_ZH = re.compile(r"^==\s*(?:经历|角色经历|History)\s*==\s*$", re.MULTILINE)
# 插入锚点：en 的章节顺序 Appearance/Personality/History/Abilities/...
ANCHOR_AFTER = ("性格", "外貌")
ANCHOR_BEFORE = ("能力", "你知道吗", "注释与外部链接")


def section_spans(text, pattern=HIST_ZH):
    """返回 [(m, 章节正文起止)] —— 二级标题匹配与其到下一个二级标题的范围。"""
    out = []
    for m in pattern.finditer(text):
        nxt = re.search(r"^==[^=]", text[m.end() :], re.MULTILINE)
        end = m.end() + nxt.start() if nxt else len(text)
        out.append((m, end))
    return out


def clean_sub_body(text):
    """子页源码 → 可并入主页面的正文：剥页首页尾、降标题一级。"""
    body = text
    # 页首模板行（Init/To do 裸形式）
    body = re.sub(r"^(?:\{\{Init\}\}\n?|\{\{To ?do\}\}\n?)+", "", body)
    body = LLM_MARK.sub("", body)
    # 页尾分类与语言链接
    lines = body.splitlines()
    while lines and (
        not lines[-1].strip()
        or re.match(r"\[\[(?:Category|分类):", lines[-1])
        or re.match(r"\[\[[a-z-]+:", lines[-1], re.IGNORECASE)
    ):
        lines.pop()
    body = "\n".join(lines).strip()
    assert body, "子页正文为空"
    # 标题降一级（== → ===）
    body = re.sub(
        r"^={2,5}(?=[^=])|(?<=[^=])={2,5}$",
        lambda m: m.group(0) + "=",
        body,
        flags=re.MULTILINE,
    )
    # 子页自带的同名一级标题（== 經歷/经历/角色经历 ==）与新章节名重复，丢弃
    body = re.sub(r"^===+\s*(?:經歷|经历|角色经历|角色經歷)\s*===+\s*\n+", "", body)
    return body.strip()


def merge_main(main_text, sub_body, title):
    """把子页正文并入主页面 == 经历 == 章节，返回新源码。"""
    # 子页的参考文献小节并入主页面页尾共享（主页面有 <references /> 时）
    if "<references" in main_text:
        sub_body = re.sub(
            r"\n*===+\s*注释与外部链接\s*===+\s*\n*<references\s*/?>\s*$",
            "",
            sub_body,
        ).rstrip()
    spans = section_spans(main_text)
    if spans:
        # 已有历史类章节（菲莉丝=重复内容、梅尔蒂=英文残留）：替换正文
        assert len(spans) == 1, f"{title} 有多个历史类章节"
        m, end = spans[0]
        return main_text[: m.start()] + f"== 经历 ==\n{sub_body}\n\n" + main_text[end:]
    for name in ANCHOR_AFTER:
        spans = section_spans(
            main_text, re.compile(rf"^==\s*{name}\s*==\s*$", re.MULTILINE)
        )
        if spans:
            m, end = spans[0]
            return (
                main_text[:end].rstrip()
                + f"\n\n== 经历 ==\n{sub_body}\n\n"
                + main_text[end:].lstrip("\n")
            )
    for name in ANCHOR_BEFORE:
        m = re.search(rf"^==\s*{name}\s*==\s*$", main_text, re.MULTILINE)
        if m:
            return (
                main_text[: m.start()].rstrip()
                + f"\n\n== 经历 ==\n{sub_body}\n\n"
                + main_text[m.start() :]
            )
    # 兜底：语言链接块之前
    tail = re.search(r"(?:\n\[\[[a-z-]+:[^\n]+\])+\s*$", main_text, re.IGNORECASE)
    at = tail.start() if tail else len(main_text)
    return main_text[:at].rstrip() + f"\n\n== 经历 ==\n{sub_body}\n" + main_text[at:]


def main():
    zh = pywikibot.Site("zh", "re0")
    en = pywikibot.Site("en", "re0")
    if not SIMULATE:
        zh.login()
        assert zh.user() == "IchiSanNi"
        rights = zh.userinfo.get("rights", [])
        assert "delete" in rights, "账号无删除权限"

    targets = [t for t in TARGETS if not FILTER or FILTER in t]
    done, skipped = [], []
    for main_title in targets:
        sub_title = main_title + "/梗概"
        main_p = pywikibot.Page(zh, main_title)
        sub_p = pywikibot.Page(zh, sub_title)
        if not sub_p.exists() or sub_p.isRedirectPage():
            skipped.append((sub_title, "子页不存在或已是重定向"))
            continue

        # revalidate：en 侧结构仍与调查一致
        m = EN_LINK.search(main_p.text)
        en_title = m.group(1).split("#")[0] if m else None
        en_main = pywikibot.Page(en, en_title) if en_title else None
        en_syn = pywikibot.Page(en, en_title + "/Synopsis") if en_title else None
        if (
            not en_main
            or not en_main.exists()
            or not HIST_EN.search(en_main.text)
            or (en_syn and en_syn.exists())
        ):
            skipped.append((sub_title, f"en 侧结构已变化（en={en_title}）"))
            continue

        sub_body = clean_sub_body(sub_p.text)
        new_main = merge_main(main_p.text, sub_body, main_title)
        assert new_main != main_p.text

        if SIMULATE:
            mode = "替换既有章节" if section_spans(main_p.text) else "新增章节"
            print(f"--- {main_title} ---")
            print(
                f"[{mode}] 子页正文 {len(sub_body)} 字符；主页面 {len(main_p.text)} → {len(new_main)} 字符"
            )
            print(f"子页正文开头: {sub_body[:80]!r}")
            print(f"子页正文结尾: {sub_body[-80:]!r}")
            continue

        main_p.text = new_main
        main_p.save(
            "梗概子页并回主页面：经历章节（结构对齐 en，History 在主页面）", bot=True
        )
        sub_p.delete(
            "内容已并入主页面经历章节（en 无对应 /Synopsis 子页）",
            prompt=False,
        )
        done.append(main_title)
        print(f"OK {main_title}")

    print(f"\n=== {'DRY RUN ' if SIMULATE else ''}结果 ===")
    print(f"完成 {len(done)}，跳过 {len(skipped)}")
    for t, why in skipped:
        print(f"  跳过 {t}: {why}")


if __name__ == "__main__":
    main()
