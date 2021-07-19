from ..jobs_ import CmdJob, add_job

add_job(
    CmdJob(
        [
            "replace",
            "-automaticsummary",
            "-always",
            "-fix:HTML",
            "-fix:syntax",
            "-fix:isbn",
            "-fix:specialpages",
        ]
    )
)
