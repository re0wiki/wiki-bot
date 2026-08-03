# 待办与待决策项

跨任务的待办与决策记录。单个领域（模板/Module）的领域知识归 `templates.md` / `modules.md`。
已完成的待办若不再需要相关信息就直接删除，不留完成记录（有长期价值的知识并入对应领域文档；执行历史查 git）。

## 模板复查（2026-08-03 第三轮）发现

第三轮新扫维度：模板间调用完整性、#invoke 目标存在性、字面文件红链、模板体参数 vs
/doc templatedata、繁简复扫。确认干净：调用/Module/文件引用/CSS 链/索引条目全部完好，
结构指标不变（227 页/55 顶层/文档 55/55/真零引用仅 Sandbox）。

### A. 值得修

1. **`Infobox character` 的 `another translation` 参数**（label 台版译名）：全站唯一带空格的
   参数名，违反 2026-08-02 归一的 snake_case 约定；~300 个角色页在用，且 templatedata 完全
   没声明它。改名走完整 SOP（见 `templates.md`），新名待定（候选 `name_zh_tw`——注意 voice
   族现状是连字符 `voice_zh-tw`，一并定夺）。修前先把该参数补进 templatedata。
2. **`QUOTE/doc` 与 `Quote/doc` 声明了无效的 `small` 参数**：两个模板体都硬编码
   （QUOTE `small=` 大字、Quote `small=1` 小字），传 small 不生效。摘 templatedata 里的
   small 声明或改写说明为「字体大小由模板选择决定」。

### B. 可选规范化（渲染无差异，纯源码卫生）

3. 小写 `#invoke` 归一：`interwiki`（Infobox battle/character、To do×2）、`tab`（Tab）
   → 实际模块名 `Interwiki`/`Tab`。功能等价（首字母大写规范化兜底），纯一致性。
4. 13 个 Tab 子页的链接**显示文本**为繁体（如 `[[小说:拉姆拒绝搭讪记|拒絕搭訕記]]`，
   链接目标全是简体）——langconv 渲染正确，归一简体只是源码规范。清单：
   Anastasia's/Emilia's/Ram's/Rem's Side Story、Julius's Notebook、Kararagi Reaper、
   Priscilla's Cheers、Sword Demon Love Story、Nascent Wolves、Oni Sisters（+/Neko）、
   Joshua's Encyclopedia。链接目标已全量核实**无红链**；其中 3 条经重定向
   （Joshua's Encyclopedia 全繁目标、Nascent Wolves×2），修显示文本时可顺手直连。
   另注：`小说:新生狼之國/佛拉基亚華麗皇帝的工作` 条目本身标题仍含繁体（國/華麗），
   属译名表范畴，不在模板整改内。
5. （ns8 顺带发现，非模板）`MediaWiki:Common.js` 注释「保證每一語言有值」繁体。

## 已决策（2026-07-31）

### 图片删除/改名不同步（re0_image 只增不删）——维持现状

残留图片基本无害；删除还要同步更新引用，不值得处理。限制已注明在 `calc_diff` docstring。

### `.idea/` 已跟踪文件——维持现状

自带 .gitignore 模板没忽略那些文件所以提交了；项目无其他维护者，交上去至少无害。

### re0_redirect 对未登记前缀建重定向——维持现状

多余重定向无用但无害。

## 已评估、决定不做

### probe_* 五个探测脚本不合并且保留样板重复

`docs/cloudflare-429.md` 按文件名逐一引用这些脚本作为实证出处（哪个脚本跑出哪组数据），
合并会破坏可追溯性；它们是一次性研究脚本而非维护中的工具，重复的样板没有维护成本。
