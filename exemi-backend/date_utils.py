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

def get_days_remaining(dt: datetime | None, australia_tz: str = "Australia/Sydney") -> int | None:
    """
    Calculate the number of calendar days between
    now and a given date and return the result.

    Args:
        dt (datetime | None): Input datetime, can be naive (assumed UTC) or tz-aware.
        australia_tz (str, optional): Target Australian timezone. Defaults to "Australia/Sydney".

    Returns:
        int | None: Number of calendar days left.
    """

    dt_aus = parse_timestamp(dt, australia_tz=australia_tz)
    if not dt_aus: return None
    current_time = datetime.now(ZoneInfo(australia_tz))
    days_difference = cal_days_diff(dt_aus, current_time)
    return days_difference

def get_days_remaining_string(dt: datetime | None, australia_tz: str = "Australia/Sydney") -> str:
    """
    Calculate the number of calendar days between
    now and a given date and return the result
    in the format "X days left", or "Unknown days left"
    if the date is None.

    Args:
        dt (datetime | None): Input datetime, can be naive (assumed UTC) or tz-aware.
        australia_tz (str, optional): Target Australian timezone. Defaults to "Australia/Sydney".

    Returns:
        str: A string representing the number of days left in the format "X days left".
    """

    days_difference = get_days_remaining(dt=dt, australia_tz=australia_tz)
    if not days_difference: return "Unknown days left"
    return str(days_difference) + " days left"

def timestamp_to_string(dt: datetime | None, australia_tz: str = "Australia/Sydney", include_time : bool = True, include_days_remaining : bool = True) -> str:
    """
    Converts a datetime (naive UTC or any tz-aware) to a specified
    Australian timezone and returns a human-readable string.

    Args:
        dt (datetime | None): Input datetime, can be naive (assumed UTC) or tz-aware.
        australia_tz (str, optional): Target Australian timezone. Defaults to "Australia/Sydney".
        include_time (bool, optional): Includes the time as well as the date. Defaults to True.
        include_days_remaining (bool, optional): Appends the number of days remaining in the format "(X days left)" to the end of the string. Defaults to True.

    Returns:
        str: Datetime string in the format: Monday, 08/02/2026, 05:30 PM (3 days left)
    """

    # Step 1: Convert to Australian timezone
    dt_aus = parse_timestamp(dt, australia_tz=australia_tz) 
    if dt_aus is None: return "Unknown"
    
    time_format = "%A, %d/%m/%Y, %I:%M %p" if include_time else "%A, %d/%m/%Y"

    # Step 2: Format as readable string
    readable_str = dt_aus.strftime(time_format)

    # Step 3: Get a string representing the number of days remaining
    if include_days_remaining:
        days_remaining_text = get_days_remaining_string(dt_aus)
        readable_str += f" ({days_remaining_text})"

    return readable_str
