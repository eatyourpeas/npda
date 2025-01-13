from datetime import date
from dateutil.relativedelta import relativedelta


# TODO MRB: How will we add new audit years (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/481)
SUPPORTED_AUDIT_YEARS = [
    # submitted on the old platform, re-uploaded to test this one
    2023,
    2024,
    # first year submitted on this platform
    2025,
    2026
]

def get_audit_period_for_date(input_date: date) -> tuple[date, date]:
    """Get the start and end date of the audit period for the given date.

    :param date: The date
    :return: (audit_start_date, audit_end_date)

    Data:
        Audit Period	Audit period start	Audit period end
        2023 - 2024	        1-Apr-23	        31-Mar-24
        2024 - 2025	        1-Apr-24	        31-Mar-25
        2025 - 2026	        1-Apr-25	        31-Mar-26

    NOTE: dates outside of the audit period will raise
          a ValueError as undefined.
    """

    if input_date < date(SUPPORTED_AUDIT_YEARS[0], 4, 1) or input_date > date(SUPPORTED_AUDIT_YEARS[-1], 3, 31):
        raise ValueError(
            f"Audit period is only available for the years 2024 to 2027. Provided date: {input_date}"
        )

    # Audit year is the year of the input date if the month is April or later, otherwise it is the previous year
    audit_year = (
        input_date.year if input_date.month >= 4 else input_date.year - 1
    )

    # Start date is always 1st April
    audit_start_date = date(audit_year, 4, 1)

    # End date is always 31st March of the following year
    audit_end_date = date(audit_year + 1, 3, 31)

    return audit_start_date, audit_end_date


def get_current_audit_year() -> int:
    (start_date, _) = get_audit_period_for_date(date.today())
    return start_date.year


def get_quarters_for_audit_period(
    audit_start_date: date, audit_end_date: date
) -> list[tuple[date, date]]:
    """Get the quarters for the audit period.

    :param audit_start_date: The start date of the audit period
    :param audit_end_date: The end date of the audit period
    :return: A list of tuples, each containing the start and end date of a quarter
    """

    # Ensure audit_start_date is earlier than audit_end_date
    if audit_start_date >= audit_end_date:
        raise ValueError("Audit start date must be before the audit end date.")

    # Initialize the list of quarters
    quarters = []

    # Calculate the start and end date of each quarter
    current_start = audit_start_date
    while current_start < audit_end_date:
        # Calculate the quarter end date by adding 3 months
        current_end = (
            current_start + relativedelta(months=3) - relativedelta(days=1)
        )

        # If the quarter end date exceeds the audit end date, use the audit end date
        if current_end > audit_end_date:
            current_end = audit_end_date

        quarters.append((current_start, current_end))

        # Move to the next quarter
        current_start = current_end + relativedelta(days=1)

    return quarters


def get_quarter_for_visit(
    visit_date: date,
) -> int:
    """Returns quarter for the visit date"""
    audit_start_date, audit_end_date = get_audit_period_for_date(visit_date)
    quarters = get_quarters_for_audit_period(audit_start_date, audit_end_date)

    for i, (quarter_start, quarter_end) in enumerate(quarters, start=1):
        if quarter_start <= visit_date <= quarter_end:
            return i

    raise ValueError("Visit date is not within the audit period.")
