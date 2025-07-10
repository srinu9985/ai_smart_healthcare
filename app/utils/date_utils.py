# app/utils/date_utils.py

from datetime import datetime, date
from typing import Union


def calculate_age(date_of_birth: Union[str, date]) -> int:

    if isinstance(date_of_birth, str):
        birth_date = datetime.strptime(date_of_birth, '%d-%m-%Y').date()
    else:
        birth_date = date_of_birth

    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


def format_date(date_obj: date, format_string: str = '%d-%m-%Y') -> str:
    """Format date object to string"""
    return date_obj.strftime(format_string)


def parse_date(date_string: str, format_string: str = '%d-%m-%Y') -> date:
    """Parse date string to date object"""
    return datetime.strptime(date_string, format_string).date()


def is_valid_date(date_string: str, format_string: str = '%d-%m-%Y') -> bool:
    """Check if date string is valid"""
    try:
        datetime.strptime(date_string, format_string)
        return True
    except ValueError:
        return False


def days_between(start_date: Union[str, date], end_date: Union[str, date]) -> int:
    """Calculate days between two dates"""
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    if isinstance(end_date, str):
        end_date = parse_date(end_date)

    return (end_date - start_date).days