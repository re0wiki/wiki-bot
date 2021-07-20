from .jobs_ import CmdJob, FuncJob, add_job, jobs


def update_doc():
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
