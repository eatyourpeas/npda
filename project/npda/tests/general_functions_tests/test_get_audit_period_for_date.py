import logging
import pytest
from datetime import date
from dateutil.relativedelta import relativedelta

from project.npda.general_functions import get_audit_period_for_date
from project.npda.general_functions.audit_period import get_quarters_for_audit_period

# Logging
logger = logging.getLogger(__name__)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "input_date,expected_date_bounds",
    [
        (
            date(2023, 4, 1),
            (date(2023, 4, 1), date(2024, 3, 31)),
        ),  # Start of the 2023 audit year
        (
            date(2024, 3, 31),
            (date(2023, 4, 1), date(2024, 3, 31)),
        ),  # End of the 2023 audit year
        (
            date(2024, 4, 1),
            (date(2024, 4, 1), date(2025, 3, 31)),
        ),  # Start of the 2024 audit year
        (
            date(2025, 3, 31),
            (date(2024, 4, 1), date(2025, 3, 31)),
        ),  # End of the 2024 audit year
        (
            date(2025, 4, 1),
            (date(2025, 4, 1), date(2026, 3, 31)),
        ),  # Start of the 2025 audit year
        (
            date(2026, 3, 31),
            (date(2025, 4, 1), date(2026, 3, 31)),
        ),  # End of the 2025 audit year
    ],
)
def test_get_audit_period_for_date_returns_correct_start_and_end_date_bounds(
    input_date, expected_date_bounds
):
    assert get_audit_period_for_date(input_date) == expected_date_bounds


def test_ensure_error_raised_for_date_outside_audit_period():
    """
    Test that a ValueError is raised when a date outside the audit period is passed to the function:

    - date(2023, 3, 31) is before
    - date(2027, 4, 1) is after
    """

    with pytest.raises(ValueError):
        get_audit_period_for_date(date(2023, 3, 31))

    with pytest.raises(ValueError):
        get_audit_period_for_date(date(2028, 4, 1))


@pytest.mark.parametrize(
    "audit_start_date,audit_end_date,expected_quarters",
    [
        (
            date(2024, 4, 1),
            date(2025, 3, 31),
            [
                (date(2024, 4, 1), date(2024, 6, 30)),
                (date(2024, 7, 1), date(2024, 9, 30)),
                (date(2024, 10, 1), date(2024, 12, 31)),
                (date(2025, 1, 1), date(2025, 3, 31)),
            ],
        ),
        (
            date(2025, 4, 1),
            date(2026, 3, 31),
            [
                (date(2025, 4, 1), date(2025, 6, 30)),
                (date(2025, 7, 1), date(2025, 9, 30)),
                (date(2025, 10, 1), date(2025, 12, 31)),
                (date(2026, 1, 1), date(2026, 3, 31)),
            ],
        ),
        (
            date(2026, 4, 1),
            date(2027, 3, 31),
            [
                (date(2026, 4, 1), date(2026, 6, 30)),
                (date(2026, 7, 1), date(2026, 9, 30)),
                (date(2026, 10, 1), date(2026, 12, 31)),
                (date(2027, 1, 1), date(2027, 3, 31)),
            ],
        ),
    ],
)
def test_get_quarters_for_audit_period(
    audit_start_date, audit_end_date, expected_quarters
):
    quarters = get_quarters_for_audit_period(audit_start_date, audit_end_date)
    assert quarters == expected_quarters
