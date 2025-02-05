from typing import Iterable
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.conf import settings


class PatientSubmission(models.Model):
    """
    The Submission class.

    This class is used to define the audit submission of patients that are being audited. The model tracks which audit year and quarter the submission relates to
    and the PZ code of the Paediatric Diabetes Unit that is conducting the audit.
    Each submission comprises  a list of unique patients and their visits as well as the csv file as a BinaryField.
    """

    patient = models.ForeignKey(
        on_delete=models.CASCADE,
        to="npda.Patient",
    )

    submission = models.ForeignKey(
        on_delete=models.CASCADE,
        to="npda.Submission",
    )

    class Meta:
        verbose_name = "PatientSubmission"
        verbose_name_plural = "PatientSubmissions"

    def __str__(self) -> str:
        return f"{self.submission} for {self.patient}"


def save(self, *args, **kwargs):
    # Check for existing submissions for the same patient and audit year
    if (
        PatientSubmission.objects.filter(
            (
                Q(patient__nhs_number=self.patient__nhs_number)
                | Q(
                    patient__unique_reference_number=self.patient__unique_reference_number
                )
            ),
            submission__audit_year=self.submission.audit_year,
        )
        .exclude(pk=self.pk)
        .exists()
    ):
        raise ValidationError("A patient can have only one submission per audit year.")
    super().save(*args, **kwargs)
