import logging

import src.utils.aws as aws
import src.utils.calamari as calamari
import src.utils.jira as jira
import src.utils.settings as settings
from src.utils.date import get_month_range_yesterday


def sync_absences():
    ignored_employees = settings.get("calamari_absence_ignored_employees").split(",")
    absence_issue = settings.get("jira_absence_issue")
    absence_worklogs = jira.fetch_absences()

    conflicts = {}
    for employee in calamari.get_employees():
        employee_email = employee["email"]

        if employee_email in ignored_employees:
            logging.debug("Ignoring absences of %s", employee_email)
            if employee_email in absence_worklogs:
                conflicts[employee_email] = absence_worklogs[employee_email]
            continue

        employee_absences = calamari.filter_absences(
            employee_email,
            calamari.get_approved_absences(employee_email)
        )

        if employee_absences == absence_worklogs[employee_email]:
            logging.info("No conflicts for user %s", employee_email)
            continue

        logging.debug("%s %s", employee_email, employee_absences)
        for absence in employee_absences:
            if absence in absence_worklogs[employee_email]:
                logging.debug("Worklog for absence of %s exists on %s", employee_email, absence["date"])
                absence_worklogs[employee_email].remove(absence)
                continue

            logging.info("Worklog for absence of %s is missing on %s (%s hours)", employee_email, absence["date"], absence["amount"])
            jira_account_id = jira.get_account_id(employee_email)
            jira.create_absence_worklog(absence_issue, absence["amount"]*3600, absence["date"], jira_account_id)

        if len(absence_worklogs[employee_email]) > 0:
            conflicts[employee_email] = absence_worklogs[employee_email]

    msg = _prepare_conflicts_message(conflicts)
    aws.send_email("Absence sync report", msg, settings.get("notification_emails").split(","))


def _prepare_conflicts_message(conflicts: dict) -> str:
    message = """
    <html>
    <head>
        <style>
            .g-table {
            border: solid 3px #DDEEEE;
            border-collapse: collapse;
            border-spacing: 0;
            font: normal 14px Roboto, sans-serif;
            }

            .g-table th {
            background-color: #DDEFEF;
            border: solid 1px #DDEEEE;
            color: #336B5B;
            min-width: 72px;
            padding: 10px;
            text-align: left;
            text-shadow: 1px 1px 1px #fff;
            }

            .g-table td {
            border: solid 1px #DDEEEE;
            color: #333;
            padding: 10px;
            }
        </style>
    </head>
    <body>
    <h3>Absence worklog conflicts</h3>
    """

    if len(conflicts) == 0:
        message += "<p>No conflicts today!</p></body></html>"
        return message

    message += """
    <table class="g-table">
    <tr>
        <th>Employee</th>
        <th>Date</th>
        <th>Amount</th>
    </tr>
    """

    for email, worklogs in conflicts.items():
        for date, amount in worklogs:
            message += f"""
            <tr>
                <td>{email}</td>
                <td>{date}</td>
                <td>{amount}</td>
            </tr>
            """

    message += "</table></body></html>"
    return message


def sync_timesheets():
    contract_types = settings.get("calamari_timesheet_contract_types").split(",")

    for employee in calamari.get_employees():
        if employee["contractType"]["name"] not in contract_types:
            logging.debug("Skipping %s", employee["email"])
            continue

        jira_account_id = jira.get_account_id(employee["email"])
        month_start, month_end = get_month_range_yesterday()

        jira_worklogs = jira.fetch_worklogs(
            jira_account_id, month_start.date().isoformat(), month_end.date().isoformat()
        )
        calamari_timesheet = calamari.fetch_timesheets(
            employee["email"], month_start.date().isoformat(), month_end.date().isoformat()
        )

        _compare_worklogs_with_timesheet(employee["email"], jira_worklogs, calamari_timesheet)


def _compare_worklogs_with_timesheet(employee_email: str, jira_worklogs: list, calamari_timesheet: list):
    jira_sum = jira.sum_worklogs(jira_worklogs)
    calamari_sum = calamari.sum_timesheets(calamari_timesheet)

    for day in jira_sum:
        if jira_sum[day] == calamari_sum[day]:
            logging.info("Calamari timesheet for %s is in sync with Jira worklogs on day %s", employee_email, day)
            continue

        # remove old entry from timesheet if necessary
        if calamari_sum[day] > 0:
            for entry in calamari_timesheet:
                if day == entry["started"][0:10]:
                    logging.debug("Deleting timesheet entry for %s on day %s", employee_email, day)
                    calamari.delete_timesheet(int(entry["id"]))

        # create an entry in timesheet
        logging.info("Creating timesheet entry for %s on day %s (hours %s)", employee_email, day, jira_sum[day])
        calamari.create_timesheet(employee_email, day, jira_sum[day])

    for day in [d for d in calamari_sum if d not in jira_sum]:
        for worklog in calamari_timesheet:
            if day == worklog["started"][0:10]:
                logging.info("Deleting timesheet entry for %s on day %s", employee_email, day)
                calamari.delete_timesheet(int(worklog["id"]))
