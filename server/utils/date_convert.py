from datetime import date, datetime
from typing import Optional

DATE_FORMAT = "%Y-%m-%d"


def parse_birthday(value: Optional[str]) -> Optional[date]:
    """Return a date for a 'YYYY-MM-DD' string, or None when it is not valid."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()
    except (ValueError, AttributeError):
        return None


def is_valid_birthday(value: Optional[str]) -> bool:
    parsed = parse_birthday(value)
    return parsed is not None and date(1900, 1, 1) <= parsed <= date.today()


def calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
    """Age in whole years, or None when the stored birthday is missing/invalid."""
    birth_date = parse_birthday(birth_date_str)
    if birth_date is None:
        return None
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return max(age, 0)
