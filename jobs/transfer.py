from .jobs_ import Job, add_job

add_job(
    Job(
        [
            "transferbot",
            "-lang:en",
            "-tolang:zh",
            "-start",
        ]
    )
)

add_job(
    Job(
        [
            "transferbot",
            "-family:w",
            "-lang:zh",
            "-tofamily:re0",
            "-tolang:zh",
            "-start:mediawiki:!",
            "-titleregex:Gadget.*css",
            "-overwrite",
        ]
    )
)
