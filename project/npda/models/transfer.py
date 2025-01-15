# python imports

# django imports
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.db import models
from django.contrib.gis.db.models import DateField, PositiveSmallIntegerField
from ...constants import *

# npda imports
from ...constants import (
    LEAVE_PDU_REASONS,
    CAN_ALLOCATE_NPDA_LEAD_CENTRE,
    CAN_DELETE_NPDA_LEAD_CENTRE,
    CAN_EDIT_NPDA_LEAD_CENTRE,
    CAN_TRANSFER_NPDA_LEAD_CENTRE,
)


class Transfer(models.Model):
    """
    This model is used to store information about a user's transfer between Paediatric Diabetes Units
    It is the middle table in the many-to-many relationship between Patient and PaediatricDiabetesUnit
    """

    date_leaving_service = DateField(
        verbose_name="Date of leaving service", blank=True, null=True
    )

    reason_leaving_service = PositiveSmallIntegerField(
        verbose_name="Reason for leaving service",
        choices=LEAVE_PDU_REASONS,
        blank=True,
        null=True,
    )

    # relationships
    paediatric_diabetes_unit = models.ForeignKey(
        to="npda.PaediatricDiabetesUnit",
        on_delete=models.CASCADE,
        related_name="patients",
    )

    patient = models.ForeignKey(
        to="npda.Patient",
        on_delete=models.CASCADE,
        related_name="paediatric_diabetes_units",
    )

    class Meta:
        verbose_name = "Transfer"
        verbose_name_plural = "Transfers"
        permissions = [
            CAN_ALLOCATE_NPDA_LEAD_CENTRE,
            CAN_DELETE_NPDA_LEAD_CENTRE,
            CAN_EDIT_NPDA_LEAD_CENTRE,
            CAN_TRANSFER_NPDA_LEAD_CENTRE,
        ]

    def __str__(self) -> str:
        if self.date_leaving_service:
            return f"Transfer record for {self.patient} from PZ Code: {self.previous_pz_code} to PZ Code: {self.paediatric_diabetes_unit.pz_code} on {self.date_leaving_service}"
        return f"{self.patient} data submitted from PZ Code: {self.paediatric_diabetes_unit.pz_code}. No previous transfers are recorded."
