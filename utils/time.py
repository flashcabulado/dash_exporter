import datetime
import pytz


def to_local(dt: datetime.datetime, tz_info: str = "UTC") -> datetime.datetime:
    try:
        tz = pytz.timezone(tz_info)
    except Exception:
        tz = pytz.utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt.astimezone(tz)


def fmt_time(dt: datetime.datetime, military: bool = True, tz_info: str = "UTC") -> str:
    dt = to_local(dt, tz_info)
    fmt = "%H:%M" if military else "%I:%M %p"
    return dt.strftime(fmt).lstrip("0") or "0"


def fmt_date(dt: datetime.datetime, tz_info: str = "UTC") -> str:
    dt = to_local(dt, tz_info)
    return dt.strftime("%d/%m/%Y")


def fmt_full(dt: datetime.datetime, military: bool = True, tz_info: str = "UTC") -> str:
    return f"{fmt_date(dt, tz_info)} {fmt_time(dt, military, tz_info)}"


def same_day(a: datetime.datetime, b: datetime.datetime, tz_info: str = "UTC") -> bool:
    return to_local(a, tz_info).date() == to_local(b, tz_info).date()
