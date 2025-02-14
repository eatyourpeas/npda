# python imports
from datetime import date
import logging
from datetime import timedelta

# django imports
from django.contrib.gis.db import models
from django.contrib.gis.db.models import (
    CharField,
    DateField,
    PositiveSmallIntegerField,
    PointField,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from project.npda.models.custom_validators import (
    validate_nhs_number,
    validate_unique_reference_number,
)

# npda imports
from ...constants import (
    ETHNICITIES,
    DIABETES_TYPES,
    SEX_TYPE,
    CAN_LOCK_CHILD_PATIENT_DATA_FROM_EDITING,
    CAN_UNLOCK_CHILD_PATIENT_DATA_FROM_EDITING,
    CAN_OPT_OUT_CHILD_FROM_INCLUSION_IN_AUDIT,
)
from ..general_functions import stringify_time_elapsed

# Logging
logger = logging.getLogger(__name__)


class Patient(models.Model):
    """
    The Patient class.

    The index of multiple deprivation is calculated using the postcode supplied and the RCPCH Census Platform

    Custom methods age and age_days, returns the age
    """

    nhs_number = CharField(  # the NHS number for England and Wales
        "NHS Number",
        unique=False,
        validators=[validate_nhs_number],
        null=True,
        blank=True,
        help_text="This is the NHS number for England and Wales. It is used to identify the patient in the audit.",
    )

    unique_reference_number = CharField(
        "Unique Reference Number",
        max_length=50,
        unique=False,
        validators=[validate_unique_reference_number],
        blank=True,
        null=True,
        help_text="This is a unique reference number for Jersey patients. It is used to identify the patient in the audit.",
    )

    sex = models.IntegerField("Stated gender", choices=SEX_TYPE, blank=True, null=True)

    date_of_birth = DateField("date of birth (YYYY-MM-DD)")
    postcode = CharField(
        "Postcode of usual address",
        blank=True,
        null=True,
    )

    location_wgs = PointField(
        help_text="longitude and latitude of the postcode as British National Grid (BNG)",
        srid=27700,
        null=True,
        blank=True,
    )

    location_bng = PointField(
        help_text="longitude and latitude of the postcode as British National Grid (BNG)",
        srid=27700,
        null=True,
        blank=True,
    )

    location_wgs84 = PointField(
        help_text="longitude and latitude of the postcode as WGS 84",
        srid=4326,
        null=True,
        blank=True,
    )

    ethnicity = CharField(
        "Ethnic Category", max_length=4, choices=ETHNICITIES, blank=True, null=True
    )

    index_of_multiple_deprivation_quintile = models.PositiveSmallIntegerField(
        # this is a calculated field - it relies on the availability of the RCPCH Census Platform
        # A quintile is calculated on save and persisted in the database
        "index of multiple deprivation calculated from RCPCH Census Platform.",
        blank=True,
        editable=False,
        null=True,
    )

    diabetes_type = PositiveSmallIntegerField(
        verbose_name="Diabetes Type", choices=DIABETES_TYPES
    )

    diagnosis_date = DateField(verbose_name="Date of Diabetes Diagnosis")

    death_date = models.DateField(
        verbose_name="Date of death",
        blank=True,
        null=True,
    )

    gp_practice_ods_code = models.CharField(
        verbose_name="GP Practice Code", blank=True, null=True
    )

    gp_practice_postcode = models.CharField(
        verbose_name="GP Practice postcode", blank=True, null=True
    )

    is_valid = models.BooleanField(
        verbose_name="Record is valid", blank=False, null=False, default=False
    )

    errors = models.JSONField(
        verbose_name="Validation errors", blank=True, null=True, default=None
    )

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = (
            "pk",
            "nhs_number",
            "unique_reference_number",
        )
        permissions = [
            CAN_LOCK_CHILD_PATIENT_DATA_FROM_EDITING,
            CAN_UNLOCK_CHILD_PATIENT_DATA_FROM_EDITING,
            CAN_OPT_OUT_CHILD_FROM_INCLUSION_IN_AUDIT,
        ]

    def clean(self):
        super().clean()

        if not self.nhs_number and not self.unique_reference_number:
            raise ValidationError(
                "Either NHS Number or Unique Reference Number must be provided."
            )
        if self.nhs_number and self.unique_reference_number:
            raise ValidationError(
                "Only one of NHS Number or Unique Reference Number should be provided."
            )

    def __str__(self) -> str:
        if self.unique_reference_number:
            return f"ID: {self.pk}, {self.unique_reference_number}"
        return f"ID: {self.pk}, {self.nhs_number}"

    def get_absolute_url(self):
        return reverse("patient-detail", kwargs={"pk": self.pk})

    def get_todays_date(self) -> date:
        """Simply returns today's date. Used to enable testing of the age methods"""
        return date.today()

    # class methods
    def age_days(self, today_date=None):
        """
        Returns the age of the patient in years, months and days
        This is a calculated field
        Date of birth is required
        Today's date is optional and defaults to self.get_todays_date()):
        """
        if today_date is None:
            today_date = self.get_todays_date()
        return (today_date - self.date_of_birth).days

    def age(self, today_date=None):
        """
        Returns the age of the patient in years, months and days
        This is a calculated field
        Date of birth is required
        Today's date is optional and defaults to self.get_todays_date()):
        """
        if today_date is None:
            today_date = self.get_todays_date()
        return stringify_time_elapsed(self.date_of_birth, today_date)

    def is_in_transfer_in_the_last_year(self):
        """
        Returns True if the patient is in transfer
        """
        current_audit_year = date.today().year
        if date.today().month < 4:
            current_audit_year -= 1

        audit_year_start = date(current_audit_year, 4, 1)
        audit_year_end = date(current_audit_year + 1, 3, 31)

        if self.paediatric_diabetes_units.filter(
            date_leaving_service__range=(audit_year_start, audit_year_end),
        ).exists():
            return True
        return False

    def has_completed_a_full_year_of_care(self):
        """
        Returns True if the patient has completed a full year of care
        This includes:
        - Patients who have been diagnosed with diabetes for more than a year
        - Patients who are still alive
        """

        if self.diagnosis_date:
            if (
                self.diagnosis_date + timedelta(days=365) < date.today()
                and self.death_date is None
            ):
                return True
        return False
