from .jobs_ import Job, add_job

add_job(
    Job(
        [
            "category",
            "remove",
            "-batch",
            "-from:Image Gallery",
        ]
    )
)
