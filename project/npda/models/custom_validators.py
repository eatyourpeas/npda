from django.core.exceptions import ValidationError
import nhs_number

import logging

# Logging
logger = logging.getLogger(__name__)


def validate_nhs_number(value):
    """Validate the NHS number using the nhs_number package."""
    if not nhs_number.is_valid(value):
        raise ValidationError(
            f"{value} is not a valid NHS number.",
            params={"value": value},
        )


def validate_unique_reference_number(value):
    """Validate the Unique Reference Number."""
    if not value.isdigit():
        raise ValidationError(
            f"{value} is not a valid Unique Reference Number.",
            params={"value": value},
        )
