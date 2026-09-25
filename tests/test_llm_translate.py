"""src/tools/llm_translate.py 未登记专名候选抽取的纯函数测试（不触 wiki）。"""

from repo_loader import load_module

lt = load_module("llm_translate", "src/tools/llm_translate.py")


def test_stopword_only_sequences_dropped():
    body = "The two met. Following their ambush, Carol spoke. However, she left."
    assert lt.noun_candidates(body) == []  # Carol 已登记，其余皆句首虚词


def test_unregistered_names_kept():
    body = "Zephyrion Quill fought at the Battle of the Nowhere Plains."
    cands = lt.noun_candidates(body)
    assert "Zephyrion Quill" in cands
    assert "Battle of the Nowhere Plains" in cands


def test_registered_names_dropped():
    body = "Carol served House Astrea with Grimm during the Royal Selection."
    assert lt.noun_candidates(body) == []


def test_possessive_and_house_stripped():
    assert lt.noun_candidates("House Remendis fell.") == []  # Remendis 已登记
    assert lt.noun_candidates("Zephyrion's shield broke.") == ["Zephyrion"]
    # House 前缀仅参与查重，未登记时保留完整候选
    assert lt.noun_candidates("House Quillburn fell.") == ["House Quillburn"]


def test_short_tokens_dropped():
    assert lt.noun_candidates("J. K. met A B at dawn.") == []


def test_sentence_initial_stopword_glued_to_name():
    # 句首虚词剥离开后按余下名字查重/保留
    body = "As Flugel spoke, During Meili left. After Zephyrion arrived."
    assert lt.noun_candidates(body) == ["Zephyrion"]  # Flugel/Meili 已登记
    # 结尾连接词剥离
    assert "Zephyr" in lt.noun_candidates("Zephyr of nowhere left.")


def test_heading_words_not_candidates():
    body = "== Family ==\n== History ==\n=== Appearance ===\nZephyrion Quill left."
    assert lt.noun_candidates(body) == ["Zephyrion Quill"]


def test_candidate_targets_display_and_mapping():
    conv = "=== [[角色:某某|Xeno Tralla]] ===\n参见 [[术语:某战]]。"
    mapping = {
        "Xeno Tralla": "角色:某某",
        "War of Nowhere": "术语:某战",
        "Old Home": "地点:旧宅#某段",
    }
    cands = ["Xeno Tralla", "War of Nowhere", "Old Home", "Julia"]
    assert lt._candidate_targets(cands, conv, mapping) == {
        "Xeno Tralla": "角色:某某",
        "War of Nowhere": "术语:某战",
        "Old Home": "地点:旧宅",
    }


def test_fully_registered_components_dropped():
    # 姓与名分开登记：全名各组成词均已登记则不再提示
    body = "Meili Portroute met Reid Astrea near Farsale Lugunica. Zephyrion Quill watched."
    assert lt.noun_candidates(body) == ["Zephyrion Quill"]


def test_possessive_component_dropped():
    # 组成词带 's 所有格同样按已登记查重
    body = "Leilani's Authority flared. Zephyrion's shield broke."
    assert lt.noun_candidates(body) == ["Zephyrion"]
