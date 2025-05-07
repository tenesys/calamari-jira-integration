import logging
from collections import defaultdict
from functools import cache

import requests
from requests.auth import HTTPBasicAuth

import src.utils.settings as settings
from src.utils.date import get_month_range


def jira_api_call(path: str, method: str = "GET", body: dict|None = None) -> dict:
    """ Make a call to Jira API """

    url = f"{settings.get('jira_api_url')}/rest/api/3/{path}"
    auth = HTTPBasicAuth(settings.get("jira_api_user"), settings.get("jira_api_token"))

    res = requests.request(
        method, url,
        headers={"Accept": "application/json"},
        auth=auth,
        json=body,
    )
    res.raise_for_status()
    return res.json()


def tempo_api_call(path: str|None = None, method: str = "GET", body: dict|None = None, next_url: str|None = None) -> dict:
    """ Make a call to Tempo API """

    url = f"https://api.tempo.io/4/{path}" if next_url is None else next_url
    res = requests.request(
        method, url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {settings.get('tempo_api_token')}"
        },
        json=body,
    )
    res.raise_for_status()
    return res.json()


@cache
def get_account_id(email: str) -> str:
    """ Get Jira Account ID from user email address """

    return jira_api_call(f"user/search?query={email}")[0]["accountId"]


@cache
def get_user_email(account_id: str) -> str:
    """ Get user email address from Jira Account ID """

    return jira_api_call(f"user/?accountId={account_id}")["emailAddress"]


def fetch_worklogs(jira_username: str, date_from: str, date_to: str) -> list:
    """ Fetch worklogs for user from Tempo """

    next_url = None
    result = []

    while True:
        response = tempo_api_call(f"worklogs/user/{jira_username}?from={date_from}&to={date_to}", next_url=next_url)

        for record in response["results"]:
            result.append({
                "timeSpentSeconds": record["timeSpentSeconds"],
                "startDate": record["startDate"],
                "accountId": record["author"]["accountId"],
                "displayName": record["author"]["displayName"],
                "email": get_user_email(record["author"]["accountId"]),
                "issueKey": record["issue"]["key"],
            })

        if "metadata" not in response or "next" not in response["metadata"]:
            return result

        next_url = response["metadata"]["next"]


def sum_worklogs(worklogs: list) -> dict:
    """ Sum up the number of hours worked per day """

    result = defaultdict(lambda: 0.0)
    absence_issue = settings.get("jira_absence_issue")

    for worklog in worklogs:
        if worklog["issueKey"] == absence_issue:
            continue

        result[worklog["startDate"]] += worklog["timeSpentSeconds"] / 3600

    return result


def create_absence_worklog(
    issue_id: str, time: int, day: str, user: str
):
    """ Create worklog in Tempo """

    worklog_desc = settings.get("jira_absence_worklog_description", "Absence")
    body = {
        "issueId": issue_id,
        "timeSpentSeconds": time,
        "billableSeconds": time,
        "startDate": day,
        "startTime": "08:00:00",
        "description": worklog_desc,
        "authorAccountId": user,
    }
    return tempo_api_call("worklogs", "POST", body)


def fetch_absences() -> dict:
    """ Fetch absences from Tempo """

    issue = settings.get("jira_absence_issue")
    month_start, month_end = get_month_range()
    date_filter = f"from={month_start.date().isoformat()}&to={month_end.date().isoformat()}"
    next_url = None

    results = defaultdict(lambda: [])
    while True:
        response = tempo_api_call(f"worklogs/issue/{issue}?{date_filter}", next_url=next_url)

        for record in response["results"]:
            results[get_user_email(record["author"]["accountId"])].append({
                "date": record["startDate"],
                "amount": record["timeSpentSeconds"] / 3600,
            })

        # end of the pagination
        if "metadata" not in response or "next" not in response["metadata"]:
            return results

        next_url = response["metadata"]["next"]
