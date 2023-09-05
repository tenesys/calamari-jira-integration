import datetime as dt
from collections import defaultdict

import requests
from requests.auth import HTTPBasicAuth

import src.utils.settings as settings
from src.utils.date import get_month_range


def api_call(path: str, body: dict|None = None, no_response: bool = False) -> dict|None:
    """ Make a call to Calamari API """

    url = f"{settings.get('calamari_api_url')}/api/{path}"
    auth = HTTPBasicAuth("calamari", settings.get("calamari_api_token"))

    res = requests.request(
        "POST", url,
        headers={"Accept": "application/json"},
        auth=auth,
        json=body,
    )
    res.raise_for_status()
    return res.json() if not no_response else None


def get_employees() -> list:
    """ Return a list of employees from Calamari """

    results = []
    page = 0
    while True:
        res = api_call("employees/v1/list", body={"page": page})
        results.extend(res["employees"])

        if res["currentPage"] == res["totalPages"]:
            return results

        page = res["currentPage"] + 1


def fetch_timesheets(email: str, date_from: str, date_to: str) -> list:
    """ Fetch employee timesheets from Calamari """

    return api_call("clockin/timesheetentries/v1/find", {"from": date_from, "to": date_to, "employees": [email]})


def sum_timesheets(worklogs: list) -> dict:
    """ Helper function to sum seconds worked per day """

    result = defaultdict(lambda: 0.0)
    for worklog in worklogs:
        result[worklog["started"][0:10]] += worklog["duration"]

    return result


def delete_timesheet(timesheet_id: int):
    """ Delete timesheet from Calamari """
    return api_call("clockin/timesheetentries/v1/delete", {"id": timesheet_id}, no_response=True)


def create_timesheet(person: str, shift_day: str, hours: float):
    """ Create timesheet entry in Calamari """

    shift_start = dt.datetime.fromisoformat(shift_day).replace(hour=8)
    shift_end = shift_start + dt.timedelta(hours=hours)

    body = {
        "person": person,
        "shiftStart": shift_start.isoformat(),
        "shiftEnd": shift_end.isoformat(),
    }
    api_call("clockin/timesheetentries/v1/create", body)


def get_approved_absences(employee_email: dict) -> dict:
    """ Fetch all approved absences for user """

    month_start, month_end = get_month_range()
    body = {
        "from": month_start.date().isoformat(),
        "to": month_end.date().isoformat(),
        "employees": [employee_email],
        "absenceStatuses": ["APPROVED"],
    }

    return api_call("leave/request/v1/find-advanced", body)


def get_nonworking_days(employee_email: str) -> list:
    """ Fetch holidays from Calamari """

    month_start, month_end = get_month_range()
    body = {
        "employee": employee_email,
        "from": month_start.strftime("%Y-%m-%d"),
        "to": month_end.strftime("%Y-%m-%d")
    }

    res = api_call("holiday/v1/find", body)
    return [i["start"] for i in res]


def filter_absences(employee_email: str, absences: dict) -> list:
    """ Filter absences from Calamari based on mail, type and holidays """

    ignored_types = settings.get("calamari_absence_ignored_types").split(",")
    nonworking_days = get_nonworking_days(employee_email)
    result = []

    for absence in absences:
        # skip specified absence types
        if absence["absenceTypeName"] in ignored_types:
            continue

        absence_start = dt.date.fromisoformat(absence["from"])
        absence_end = dt.date.fromisoformat(absence["to"])

        for i in range((absence_end - absence_start).days + 1):
            date = absence_start + dt.timedelta(days=i)

            # check only current month
            if date.month != dt.datetime.now().month:
                continue

            # skip non-working days and weekends
            if date.isoformat() in nonworking_days or date.weekday() > 4:
                continue

            unit = 8.0 if absence["entitlementAmountUnit"] == "DAYS" else 1.0
            hours = 8.0 # full day

            # support for half and quarter of the day
            if date.isoformat() == absence["from"] and absence["amountFirstDay"]:
                hours = absence["amountFirstDay"] * unit

            if date.isoformat() == absence["to"] and absence["amountLastDay"]:
                hours = absence["amountLastDay"] * unit

            result.append({
                "date": date.isoformat(),
                "amount": hours,
            })

    return result
