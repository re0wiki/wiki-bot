"""仓库自有代码的统一伞包。

顶层目录冻结：pwb 契约物（pwb/、families/、user-config.py、user-fixes.py、
scripts 解析由 user-config.py 的 user_script_paths 指向 src/scripts）之外，
仓库自有代码一律放本包下——src/scripts/（pwb 任务入口 + tools/ + oneoff/）、
src/jobs/（任务编排）、src/<feature>/（功能包，如 nekoquote）。
"""
