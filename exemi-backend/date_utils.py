from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

"""
Simple utilities for converting
timestamps into Australian timezones
and calculating the number of calendar
days between them.
"""

def cal_days_diff(a : datetime, b : datetime) -> int:
    """
    Calculate the number of calendar days between two dates.
    Source: Matt Alcock https://stackoverflow.com/a/17215747

    Args:
        a (datetime): Later date.
        b (datetime): Earlier date.
    
    Returns:
        days (int): The number of days between the dates.
    """
    A = a.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    B = b.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    return (A - B).days

def parse_timestamp(dt: datetime | None, australia_tz: str = "Australia/Sydney") -> datetime | None:
    """
    Converts a datetime (naive UTC or any tz-aware) to a specified
    Australian timezone.

    Args:
        dt (datetime | None): Input datetime, can be naive (assumed UTC) or tz-aware.
        australia_tz (str, optional): Target Australian timezone. Defaults to "Australia/Sydney".

    Returns:
        datetime | None: The datetime in Australian timezone.
    """

    if dt is None: return None

    # Step 1: If naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    
    # Step 2: Convert to Australian timezone
    dt_aus = dt.astimezone(ZoneInfo(australia_tz))

    return dt_aus

def timestamp_to_string(dt: datetime | None, australia_tz: str = "Australia/Sydney") -> str:
    """
    Converts a datetime (naive UTC or any tz-aware) to a specified
    Australian timezone and returns a human-readable string.

    Args:
        dt (datetime | None): Input datetime, can be naive (assumed UTC) or tz-aware.
        australia_tz (str, optional): Target Australian timezone. Defaults to "Australia/Sydney".

    Returns:
        str: Datetime string in the format: Monday, 08/02/2026, 05:30 PM (3 days from now)
    """

    # Step 1: Convert to Australian timezone
    dt_aus = parse_timestamp(dt, australia_tz=australia_tz) 
    if dt_aus is None: return "Unknown"

    # Step 2: Format as readable string
    readable_str = dt_aus.strftime("%A, %d/%m/%Y, %I:%M %p")

    # Step 3: Add the number of days remaining
    current_time = datetime.now(ZoneInfo(australia_tz))
    days_difference = cal_days_diff(dt_aus, current_time)

    readable_str += f" ({days_difference} days from now)"

    return readable_str
