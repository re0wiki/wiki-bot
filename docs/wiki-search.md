# Fandom 搜索能力（insource 等关键词支持情况）

2026-08-22 对 rezero.fandom.com 实测（API `list=search`，匿名，与 Special:Search 同后端）。

## 结论

- Fandom **没有 CirrusSearch**。全站扩展清单里搜索相关只有 `UnifiedSearch`（Fandom 自研引擎，2016 年底起替换默认搜索，官方说明见 community 中央站 `Help:Searching`）。
- 因此 MediaWiki/CirrusSearch 的高级搜索关键词**全部不可用**：`insource:`（含正则 `insource:/…/`）、`intitle:`、`hastemplate:`、`incategory:`、`linksto:`、`prefix:`。
- **失败形态是静默退化，不报错**：`insource:昴` 这类「关键词 + 冒号」token 会让整个查询返回 0 命中（即使 `昴` 裸搜有数千结果）；`prefix:漫画` 不报错但结果并非标题前缀匹配。写工具时不能靠异常发现不支持。
- 索引对象是**渲染后的文本，不是 wikitext 源码**：`<!--as-is-->` 这类只存在于源码的 HTML 注释搜不到（`as-is` 的少量「命中」是连字符被剥离后词干匹配 `as`/`is` 的噪音）。

## 实际支持的语法（官方 Help:Searching + 实测）

- 多词默认 AND（`AND`/`OR`/`NOT` 保留字已于 2016 年移除）。
- `-词` 排除；`"词"` / `"短语"` 精确整词匹配（关闭词干提取）。
- 词干提取（英语等）、字符折叠（变音符号归一）。
- `&`、`+` 等特殊符号被剥离忽略。
- API 参数 `srnamespace` 正常；Special:Search 的 Advanced 界面可选命名空间。

## 对本仓库的意义

需要**源码级检索**时（审计某模板写法、找某字符串出现位置）不能走搜索接口，按既有做法全量拉源码内存扫描（`rvprop=content`，见 AGENTS.md 坑节「派生表与源码不一致」同款原则）。搜索接口只适用于检索渲染文本。

## 实测速查

```
srsearch=昴                  -> 大量命中
srsearch=insource:昴         -> 0 命中（静默退化）
srsearch=insource:/菜月.昴/  -> 0 命中
srsearch=intitle:菜月        -> 0 命中
srsearch=hastemplate:Init    -> 0 命中
srsearch=incategory:角色     -> 0 命中
srsearch="菜月昴"            -> 精确短语命中
```
