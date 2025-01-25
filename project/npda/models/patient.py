# python imports
from datetime import date
import logging
from enum import Enum

from httpx import HTTPError

# django imports
from django.contrib.gis.db import models
from django.contrib.gis.db.models import (
    CharField,
    DateField,
    PositiveSmallIntegerField,
    PointField,
)
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from project.npda.models.custom_validators import validate_nhs_number

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

    The index of multiple deprivation is calculated in the save() method using the postcode supplied and the
    RCPCH Census Platform

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
