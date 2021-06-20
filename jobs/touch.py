from .jobs_ import CmdJob, add_job

add_job(
    CmdJob(
        [
            "touch",
            "-pt:2",
            "-transcludes:Editing",
            "-page:Category:页面状态",
        ]
    )
)
