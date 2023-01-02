from .jobs_ import CmdJob, add_job

add_job(
    CmdJob(
        [
            "category",
            "remove",
            "-batch",
            f"-from:Image Gallery",
        ]
    )
)
