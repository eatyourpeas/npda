from random import randint
from datetime import date


def random_date(start_date: date, end_date: date) -> date:
    """
    Returns a random date between the start and end date
    """
    return date.fromordinal(randint(start_date.toordinal(), end_date.toordinal()))
