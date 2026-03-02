import logging
from subprocess import CalledProcessError, run


def run_job(job: list[str], simulate=False, capture_output=False) -> str:
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
    logging.info("=" * 16 + "start" + "=" * 16)
    logging.info(cmd)
    try:
        res = run(
            cmd,
            capture_output=capture_output,
            encoding="utf8",
            shell=True,
            check=True,
        )
    except CalledProcessError as e:
        logging.error(e)
        return ""
    finally:
        logging.info(cmd)
        logging.info("=" * 16 + "end" + "=" * 16)
    return res.stdout
