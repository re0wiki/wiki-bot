import logging
from subprocess import CalledProcessError, run

logger = logging.getLogger(__name__)


def run_job(job: list[str], simulate=False, capture_output=False) -> str | None:
    # Get the command line.
    cmd = ["python", "pywikibot/pwb.py", *job]
    if simulate:
        cmd.append("-simulate")
    elif job[0] == "interwiki":
        cmd.append("-auto")
        cmd.append("-force")
    elif job[0] != "transferbot":
        cmd.append("-always")

    # Run the job.
    logger.info("=" * 16 + "start" + "=" * 16)
    logger.info(cmd)
    try:
        res = run(
            cmd,
            capture_output=capture_output,
            encoding="mbcs",
            shell=True,
            check=True,
        )
    except CalledProcessError as e:
        logger.error(e)
        return ""
    finally:
        logger.info(cmd)
        logger.info("=" * 16 + "end" + "=" * 16)
    return res.stdout
