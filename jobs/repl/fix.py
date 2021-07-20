from ..jobs_ import CmdJob, add_job

add_job(
    CmdJob(
        [
            "replace",
            "-automaticsummary",
            "-always",
            # built-in fixes
            "-fix:HTML",
            "-fix:syntax",
            "-fix:isbn",
            "-fix:specialpages",
            # user-fixes.py
            "-fix:misc",
            # "-fix:args",
            "-fix:gallery",
            "-fix:head",
        ]
    )
)
