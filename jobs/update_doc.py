from .jobs_ import CmdJob, FuncJob, add_job, jobs


def update_doc():
    """返回一个CmdJob，其作用为更新wiki上有关自动化规则的文档。"""
    return CmdJob(
        [
            "replace",
            "-summary:update doc",
            "-always",
            "-nocase",
            "-regex",
            "-dotall",
            r"(?<=<pre>\n).*(?=\n</pre>)",
            jobs.info,
            "-page:project:攻略指南",
        ],
    )


add_job(FuncJob(update_doc))
