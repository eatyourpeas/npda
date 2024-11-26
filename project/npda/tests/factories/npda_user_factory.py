"""Factory function to create new NPDAUser."""

# Standard imports
import logging
import uuid

import factory

# Project imports
from project.npda.models import NPDAUser
from project.npda.tests.factories.organisation_employer_factory import \
    OrganisationEmployerFactory
from project.npda.tests.factories.paediatrics_diabetes_unit_factory import \
    PaediatricsDiabetesUnitFactory

# Logging
logger = logging.getLogger(__name__)


class NPDAUserFactory(factory.django.DjangoModelFactory):
    """Factory for creating a minimum viable NPDAUser.

    Additionally, takes in a `organisation_employers` list of pz_codes to associate with the user.
    Associated PDU's are created if they do not exist in the db.
    """

    class Meta:
        model = NPDAUser
        skip_postgeneration_save = True

    email = factory.LazyAttribute(lambda _: f'npda_test_user_{str(uuid.uuid4())}@nhs.net')

    first_name = "Mandel"
    surname = "Brot"
    is_active = True
    is_superuser = False
    email_confirmed = True

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        # Set a default password
        self.set_password("pw")

        # Add the extracted groups if provided
        if extracted:
            for group in extracted:
                self.groups.add(group)

        self.save()

    @factory.post_generation
    def organisation_employers(self, create, extracted, **kwargs):
        if not create:
            logger.info("Not creating OrganisationEmployer instances.")
            return

        # Initialize the list to hold PaediatricDiabetesUnit instances
        pdus = []

        # If no pz_codes are provided, create a default PaediatricsDiabetesUnit and OrganisationEmployer
        if not extracted:
            default_pdu = PaediatricsDiabetesUnitFactory()
            OrganisationEmployerFactory.create(
                npda_user=self, paediatric_diabetes_unit=default_pdu
            )
            pdus.append(default_pdu)

        else:
            # If pz_codes are provided, create OrganisationEmployer for each pz_code
            for pz_code in extracted:
                pdu = PaediatricsDiabetesUnitFactory(
                    pz_code=pz_code,
                )

                OrganisationEmployerFactory.create(
                    npda_user=self, paediatric_diabetes_unit=pdu
                )
                pdus.append(pdu)

        # Set the organisation_employers field with the created PaediatricsDiabetesUnit instances
        self.organisation_employers.set(pdus)
        self.save()
