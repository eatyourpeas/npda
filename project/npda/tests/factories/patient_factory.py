"""Factory fn to create new Patient.
"""

# standard imports
from datetime import date, timedelta
from enum import Enum
import logging
import random

# third-party imports
from django.contrib.gis.geos import Point
import factory
import nhs_number
from dateutil.relativedelta import relativedelta

# rcpch imports
from project.npda.general_functions.audit_period import get_audit_period_for_date
from project.npda.general_functions.random_date import get_random_date
from project.npda.models import Patient
from project.npda.tests.factories.visit_factory import VisitFactory
from .transfer_factory import TransferFactory
from project.constants import (
    ETHNICITIES,
    DIABETES_TYPES,
    SEX_TYPE,
)

# Logging
logger = logging.getLogger(__name__)


TODAY = date.today()
DATE_OF_BIRTH = TODAY - relativedelta(years=10)

GP_POSTCODE_NO_SPACES = "SE135PJ"
GP_POSTCODE_WITH_SPACES = "SE13 5PJ"

# Mocked values
location_bng = Point(x=531000, y=180000)
location_wgs84 = Point(x=51.5074, y=0.1278)

LOCATION = location_wgs84, location_bng

VALID_FIELDS = {
    "nhs_number": "6239431915",
    "sex": SEX_TYPE[0][0],
    "date_of_birth": TODAY - relativedelta(years=10),
    "postcode": "NW1 2DB",
    "ethnicity": ETHNICITIES[0][0],
    "diabetes_type": DIABETES_TYPES[0][0],
    "diagnosis_date": DATE_OF_BIRTH + relativedelta(years=8),
    "gp_practice_ods_code": "G85023",
    "location_bng": location_bng,
    "location_wgs84": location_wgs84,
}

VALID_FIELDS_WITH_GP_POSTCODE = VALID_FIELDS | {
    "gp_practice_ods_code": None,
    "gp_practice_postcode": GP_POSTCODE_WITH_SPACES,
}

INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE = 4


class AgeRange(Enum):
    """
    Enum class to represent the range of ages for children.
    """

    AGE_0_4 = (0, 4)
    AGE_5_10 = (5, 10)
    AGE_11_15 = (11, 15)
    AGE_16_19 = (16, 19)
    AGE_20_25 = (20, 25)


class Sex(Enum):
    """
    Enum class to represent sexes for children
    """

    NOT_KNOWN = SEX_TYPE[0][0]
    MALE = SEX_TYPE[1][0]
    FEMALE = SEX_TYPE[2][0]
    NOT_SPEC = SEX_TYPE[3][0]


class PatientFactory(factory.django.DjangoModelFactory):
    """Dependency factory for creating a minimum viable Patient.

    Fills in default values if not specified at object creation.
    """

    class Meta:
        model = Patient
        skip_postgeneration_save = True

    postcode = VALID_FIELDS["postcode"]
    gp_practice_ods_code = VALID_FIELDS["gp_practice_ods_code"]

    diabetes_type = factory.lazy_attribute(lambda x: random.choice(DIABETES_TYPES)[0])
    sex = factory.lazy_attribute(lambda x: random.choice([sex.value for sex in Sex]))
    ethnicity = factory.lazy_attribute(lambda x: random.choice(ETHNICITIES)[0])

    @factory.lazy_attribute
    def nhs_number(self):
        """Returns a unique NHS number which has not been used in the db yet."""

        # First generate 5 numbers and check if they exist in the db
        candidate_nums = nhs_number.generate(
            quantity=5, for_region=nhs_number.REGION_ENGLAND
        )

        not_found_unique_nhs_number = True
        while not_found_unique_nhs_number:
            for nhs_num in candidate_nums:
                if not Patient.objects.filter(nhs_number=nhs_num).exists():
                    not_found_unique_nhs_number = False
                    return nhs_num

            # If all 5 numbers are already in the db, generate 5 more
            candidate_nums = nhs_number.generate(
                quantity=5, for_region=nhs_number.REGION_ENGLAND
            )

    @factory.lazy_attribute
    def date_of_birth(self):
        """Set date_of_birth based on the selected age_range."""
        min_age, max_age = self.age_range.value

        # Has to be at least 0 years old to be in the audit
        today = self.audit_start_date
        # Pick a random age within the range
        age = random.randint(min_age, max_age)

        # if 0 years, then age needs to be in months (minimum 1 month)
        if age == 0:
            age = random.randint(1, 11)
            return today - relativedelta(months=age)
        else:
            # Otherwise, age is in years
            return today - relativedelta(years=age)

    @factory.lazy_attribute
    def diagnosis_date(self):
        """Set diagnosis_date between date_of_birth and audit start date."""
        return get_random_date(
            start_date=self.date_of_birth, end_date=self.audit_start_date
        )

    # Once a Patient is created, we must create a Transfer object
    transfer = factory.RelatedFactory(TransferFactory, factory_related_name="patient")

    # We also create a Visit object
    visit = factory.RelatedFactory(
        VisitFactory,
        factory_related_name="patient",
    )

    # Attributes to control factory behavior
    class Params:
        audit_start_date = get_audit_period_for_date(TODAY)[
            0
        ]  # Default audit_start_date; can be overridden
        audit_end_date = get_audit_period_for_date(TODAY)[
            1
        ]  # Default audit_end_date; can be overridden
        age_range = AgeRange.AGE_11_15  # Default age range
