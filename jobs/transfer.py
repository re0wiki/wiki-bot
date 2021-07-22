from .jobs_ import CmdJob, add_job

add_job(
    CmdJob(
        [
            "transferbot",
            "-lang:en",
            "-tolang:zh",
            "-start",
        ]
    )
)

add_job(
    CmdJob(
        [
            "transferbot",
            "-family:cc",
            "-lang:zh",
            "-tofamily:re0",
            "-tolang:zh",
            "-start:mediawiki:!",
            "-titleregex:Gadget.*css",
            "-overwrite",
        ]
    )
)
