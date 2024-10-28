import random
from dateutil.relativedelta import relativedelta


def get_random_date(start_date, end_date):
    """
    Returns a random date between start_date and end_date.

    :param start_date: The earliest possible date (inclusive)
    :param end_date: The latest possible date (exclusive)
    :return: A random date between start_date and end_date
    """
    delta = end_date - start_date
    if delta.days < 0:
        raise ValueError("end_date must be greater than or equal to start_date")
    random_days = random.randint(0, delta.days - 1)
    return start_date + relativedelta(days=random_days)
