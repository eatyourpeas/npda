from django.contrib.gis.db import models
from django.contrib.gis.db.models import CharField


class PaediatricDiabetesUnit(models.Model):
    """
    This model stores the paediatric diabetes unit reference PZ code and ODS code of the associated organisation
    """

    pz_code = CharField(
        max_length=10,
        help_text="Enter the paediatric diabetes unit PZ code",
    )
    lead_organisation_ods_code = CharField(
        max_length=10,
        help_text="Enter the organisation ODS code",
    )
    lead_organisation_name = CharField(
        max_length=75,
        help_text="Enter the organisation name",
        blank=True,
        null=True,
    )
    parent_ods_code = CharField(
        max_length=10,
        help_text="Enter the parent ODS code",
        blank=True,
        null=True,
    )
    parent_name = CharField(
        max_length=75,
        help_text="Enter the parent name",
        blank=True,
        null=True,
    )
    paediatric_diabetes_network_code = CharField(
        max_length=10,
        help_text="Enter the paedidatric diabetes network PN code",
        blank=True,
        null=True,
    )
    paediatric_diabetes_network_name = CharField(
        max_length=75,
        help_text="Enter the paediatric diabetes network name",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Paediatric Diabetes Unit"
        verbose_name_plural = "Paediatric Diabetes Units"

    def __str__(self):
        return self.pz_code
