# Module（Lua）审查

2026-07-30 对 Module 命名空间 43 个页面（15 个功能模块 + 28 个鼠色猫语录数据表）的全量审查。
源码快照脚本 `scripts/dump_modules.py`（输出 `logs/modules/`），引用量与疑点验证 `scripts/oneoff/verify_module_findings.py`。

**文档惯例**：Module 的 `/doc` 子页由 Scribunto 自动转置渲染在代码上方（与模板 `{{Documentation}}` 机制无关），所以 Lua 头注释无需写「文档见 /doc」之类的指针；模块文档直接写进 `/doc` 子页即可（先例 `Module:Kana2Romaji/doc`）。2026-07-31 起全站 40 个模块均有 /doc：功能模块按 Kana2Romaji/doc 体例（导航模板首行 + `;` 定义列表，无对应 `Template:Tab/*` 的内部模块省略导航行），27 个语录数据子表统一一行说明 + 指回主模块文档。**写 /doc 的坑**：正文里的 `-{...}-` 与 `[[en:...]]` 示例必须包 `<nowiki>`（否则被 LanguageConverter 吃掉 / 变成真跨语言链接），分类提及必须前导冒号（否则 doc 页自己入分类）；`Dev:` 只是 Scribunto `require` 的前缀、**不是链接前缀**——链 dev wiki 模块要写 `[[w:c:dev:Module:Arguments|Dev:Arguments]]`。

**渲染对比的坑**：PortableInfobox 的 tab 元素 id（`pi-tab-<哈希>-N`/`pi-tabpanel-<哈希>-N`）每次 parse 随机生成——前后两次 parse 的 HTML 逐字节比较必然不等，须先归一化（`scripts/oneoff/deploy_module_cleanup.py` 的 `parse_html`）。否则会像 2026-07-30 这批一样把全部对照误判为「渲染有差异」。

**渲染对比的坑（其二）**：`action=parse` 取的是**解析缓存**，「编辑前快照」可能是数天前的陈旧渲染——deploy 首轮对比 5 项 FAIL 全是缓存噪声（连续两次 parse 完全一致可证）。真值法照旧有效：恢复旧版模块 + purge 后取的基线才是干净的。做渲染对比时务必 purge 或走真值法，否则 OK/FAIL 都可能是缓存假象。

## 引用量总览（embeddedin，全命名空间，2026-07-31 复核）

| Module | 引用 | 说明 |
|---|---|---|
| Init / Title | 2209 | 每篇文章经 `{{Init}}` 间接引用 |
| Tab | 2404 | Init 依赖 + `{{Tab}}` 直接使用 |
| Interwiki | 2198 | 信息框英文名/英译 |
| Infobox book | 719 | |
| Character image | 337 | Infobox character 图库 |
| Kana2Romaji | 260 | |
| 鼠色猫语录 | 207 | |
| Auto ruby | 149 | 经 `{{R}}` |
| Bili | 24 | 经 `{{BV}}` |
| NoteTA / WikitextLC | 1 | 仅 `Template:NoteTA`（该模板本身 2 引用） |
| Sandbox | 0 | 空沙盒模块（2026-07-30 后新建），按沙盒惯例保留 |

**引用排查的坑（2026-07-31 复核确认）**：CirrusSearch 的 insource 在本站**对模板/主空间源码同样返回空**（`insource:"#invoke:Init"` 在 ns 0|10|828 搜出 0 条，而 `Template:Init` 明明写着 `{{#invoke:Init|main}}`）——不只是 Module 空间。消费者排查唯一可靠路径：`scripts/dump_modules.py` 本地快照 grep（模块间 require）+ 模板空间全量 dump grep（`#invoke:` 调用面）。快照脚本已改为先清空 `logs/modules/` 再拉取，避免已删模块的残留文件误导 grep。

## 评估结论与备忘（勿当 bug 修）

- **`Init.display_title` 的 9 变体 `-{T|...}-`**：冗余但正确（hans+hant 两条即可覆盖全部变体回退链），改动会触发 2210 页重渲染，不值得。
- **鼠色猫语录 4 个空数据子模块**（帕克/福尔图娜/Web连载网站上评论/动画实况解说）：空 `list`/`abbr` 占位是**刻意保留**（用户：以后可能补），勿删。
- **Kana2Romaji 的 `メィ→mei`/`リィ→ri` 两条特判是必需项，勿删**（2026-07-30 考证）：它们服务 `角色:梅莉·波多尔德` 的 `name_ja_kanji = メィリィ·ポートルート`——メィリィ 是作者官方表记（なろう 6-46 节标题同款），小ぃ 不在规范拗音表内，删掉会以 `Meィriィ` 形式漏假名。输出 `Meiri` 与英文站信息框 Romaji 栏手写值一致（官方英文名是 Meili，栏位语义不同，不改）。历史：2021-03-06 建模块，次日（108839/108867）分两次针对该名补上这两条；初版表底子应抄自站外平文式表，后续フェ/フィ/フォ/ディ/ファ/ォ 等均是按与英文站手写罗马字的差异逐条打的补丁。
- **双维护点**：`Module:Title` 的 `prefixes` 与 `user-fixes.py` 的 `PSEUDO_PREFIXES` 内容相同、两处手工维护（2026-07-31 核对同步）——改前缀时两边都要动。

## 整改历史（2026-07-30/31，均已完成）

初审（07-30，3 Bug + 7 卫生问题）与复审（07-31，5 项卫生问题）发现的问题当日全部处置完毕，要点：Kana2Romaji 重写为音拍 tokenize 的完整平文式（补ヴ系/外来拗音/ん同化，修 `ヴィルヘルム→ヴィruherumu` 漏假名与首字母不大写两个 bug 及 `num` 全局泄漏；现行规则见 `Module:Kana2Romaji/doc`）；AutoTab 并入 Init（tab 探测逻辑内联，拼接改调 `Module:Tab._tab`，Module:AutoTab 及 /doc 删除）；生产代码调试日志（mw.log/mw.logObject）全删，以后出 bug 按需再加；孤儿 Module:Set、无消费者的 Module:Utils 删除（唯一活函数 `a_in_b` 内联进 Title）；Infobox book / NoteTA / 鼠色猫语录 / Init 等函数 local 化，NoteTA CGroup 死路径移除；全站 40 个模块 /doc 补齐。部署脚本在 `scripts/oneoff/`（deploy_init_merge / deploy_module_cleanup / deploy_kana2romaji / deploy_module_hygiene2 / deploy_module_docs），逐条处置细节见 git 历史。
