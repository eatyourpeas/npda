"""Factory fn to create new Visit, related to a Patient.
"""

# standard imports
import logging
from django.apps import apps

# third-party imports
import factory

# rcpch imports
from project.npda.models.paediatric_diabetes_unit import PaediatricDiabetesUnit

# Logigng
logger = logging.getLogger(__name__)


class PaediatricsDiabetesUnitFactory(factory.django.DjangoModelFactory):
    """PDU Factory.

    Defaults to Chelsea Westminster Hospital.
    """

    class Meta:
        model = PaediatricDiabetesUnit

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Custom create method to handle get_or_create logic for PaediatricsDiabetesUnit.

        This mimics a get or create operation every time a new PDUFactory instance is created.
        """
        # Chelsea Westminster Hospital defaults with PZ130
        CHELWEST_PZ_CODE = "PZ130"
        CHELWEST_ODS_CODE = "RQM01"

        pz_code = kwargs.pop("pz_code", CHELWEST_PZ_CODE)
        lead_organisation_ods_code = kwargs.pop(
            "lead_organisation_ods_code", CHELWEST_ODS_CODE
        )

        # NOTE: filtered only on pz_code as this is the most important
        # attribute. The ods_code could be 'error' or different within
        # same pz_code, so adds complexity.
        pdus = PaediatricDiabetesUnit.objects.filter(pz_code=pz_code)

        # Delete all PDUs if multiple as we need to ensure only 1.
        if pdus.count() > 1:
            logger.info(f"Found multiple PDUs! Deleting and creating one: {pdus=}")
            pdus.delete()

        # Create / update
        pdu, created = PaediatricDiabetesUnit.objects.get_or_create(pz_code=pz_code)
        pdu.pz_code = pz_code
        pdu.lead_organisation_ods_code = lead_organisation_ods_code

        pdu.save()
        return pdu
