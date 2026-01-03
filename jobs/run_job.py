import logging
from subprocess import CalledProcessError, run


def run_job(job: list[str], simulate=False, capture_output=False) -> str:
    # Preprocess the job.
    if simulate:
        if "-always" in job:
            job.remove("-always")
        job.append("-simulate")
    job[0:0] = ["python", "pywikibot/pwb.py"]

    # Run the job.
    logging.info("=" * 16 + "start" + "=" * 16)
    logging.info(job)
    try:
        res = run(
            job,
            capture_output=capture_output,
            encoding="utf8",
            check=True,
        )
    except CalledProcessError as e:
        logging.error(e)
        return ""
    finally:
        logging.info(job)
        logging.info("=" * 16 + "end" + "=" * 16)
    return res.stdout
