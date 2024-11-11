from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class Submission(models.Model):
    """
    The Submission class.

    This class is used to define the audit submission of patients that are being audited. The model tracks which audit year and quarter the submission relates to
    and the PZ code of the Paediatric Diabetes Unit that is conducting the audit.
    Each submission comprises  a list of unique patients and their visits as well as the csv file as a BinaryField.
    """

    audit_year = models.IntegerField(
        "Audit year",
        blank=False,
        null=False,
        help_text="Year the audit is being conducted",
    )

    submission_date = models.DateTimeField(
        "Submission date",
        help_text="Date the submission was created",
    )

    submission_active = models.BooleanField(
        "Submission active",
        default=True,
        help_text="Submission is active and being considered for inclusion in the audit",
    )

    submission_by = models.ForeignKey(
        on_delete=models.CASCADE,
        to="npda.NPDAUser",
    )

    csv_file = models.FileField(
        upload_to=f"submissions/csv/",
        help_text="CSV file containing the audit data for this submission",
        null=True,  # submissions that are not active will have their csv file deleted
    )
    errors = models.JSONField(
        "Errors",
        help_text="Errors that have been found in the uploaded CSV file",
        null=True,
        blank=True,
    )

    patients = models.ManyToManyField(
        to="npda.Patient", through="npda.PatientSubmission", related_name="submissions"
    )

    paediatric_diabetes_unit = models.ForeignKey(
        on_delete=models.CASCADE,
        to="npda.PaediatricDiabetesUnit",
        related_name="pdu_submissions",
    )

    def __str__(self) -> str:
        return f"Submission from {self.paediatric_diabetes_unit} for {self.audit_year}"

    class Meta:
        verbose_name = "Submission"
        verbose_name_plural = "Submissions"
        ordering = ("audit_year",)

    def delete(self, *args, **kwargs):
        if self.submission_active:
            raise ValidationError("Cannot delete an active submission.")
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.submission_active == False:
            self.csv_file.delete(
                save=True
            )  # delete the csv file if the submission is not active
            self.csv_file = (
                None  # set the csv file to None if the submission is not active
            )

        super().save(*args, **kwargs)
