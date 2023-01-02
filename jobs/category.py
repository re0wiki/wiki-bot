from .jobs_ import CmdJob, add_job

add_job(
    CmdJob(
        [
            "category",
            "remove",
            "-batch",
            "-from:Image Gallery",
        ]
    )
)
