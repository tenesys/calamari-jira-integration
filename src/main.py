import logging

import src.jobs as jobs
import src.utils.settings as settings

def lambda_handler(event, context):
    logging.getLogger().setLevel(level=logging.DEBUG if int(settings.get('debug', '0')) else logging.INFO)

    available_jobs = {
        "sync-absences": jobs.sync_absences,
        "sync-timesheets": jobs.sync_timesheets,
    }

    if event["job"] in available_jobs:
        available_jobs[event["job"]]()
    else:
        logging.error("Unknown job, please choose `sync-absences` or `sync-timesheets`")
