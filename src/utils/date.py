import datetime as dt
from functools import cache


@cache
def get_month_range() -> tuple:
    today = dt.datetime.now()
    next_month = today.replace(day=28) + dt.timedelta(days=4)

    month_start = today.replace(day=1)
    month_end = next_month - dt.timedelta(days=next_month.day)

    return month_start, month_end


@cache
def get_month_range_yesterday() -> tuple:
    today = dt.datetime.now() - dt.timedelta(days=1)
    next_month = today.replace(day=28) + dt.timedelta(days=4)

    month_start = today.replace(day=1)
    month_end = next_month - dt.timedelta(days=next_month.day)

    return month_start, month_end
