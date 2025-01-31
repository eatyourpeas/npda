"""
Test that users who do not have the can_upload_csv permission cannot save a patient through the questionnaire view.
"""

from datetime import date
import logging

# Django imports
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from django.urls import reverse

# 3rd party imports
import pytest

# E12 imports
from project.npda.tests.factories.patient_factory import PatientFactory, VALID_FIELDS
from project.npda.tests.factories.paediatrics_diabetes_unit_factory import (
    PaediatricsDiabetesUnitFactory,
)
from project.constants.user import RCPCH_AUDIT_TEAM
from project.npda.forms.patient_form import PatientForm
from project.npda.forms.visit_form import VisitForm
from project.npda.models import NPDAUser, Visit
from project.npda.models import Patient
from project.npda.tests.utils import login_and_verify_user
from project.npda.tests.UserDataClasses import test_user_audit_centre_editor_data
from project.npda.general_functions import audit_period
from project.npda.tests.factories.visit_factory import VisitFactory, COMPLETED_VISIT

logger = logging.getLogger(__name__)

ALDER_HEY_PZ_CODE = "PZ074"
ALDER_HEY_ODS_CODE = "RBS25"

GOSH_PZ_CODE = "PZ196"
GOSH_ODS_CODE = "RP401"

audit_dates = audit_period.get_audit_period_for_date(date.today())


from httpx import HTTPError
from django.core.exceptions import ValidationError

from project.npda.tests.factories.patient_factory import (
    VALID_FIELDS,
    VALID_FIELDS_WITH_GP_POSTCODE,
    INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE,
    GP_POSTCODE_WITH_SPACES,
)

from project.npda.forms.external_patient_validators import validate_patient_async


@pytest.mark.django_db
class TestQuestionnaireView:
    @pytest.fixture(autouse=True)
    def setup(self, seed_groups_fixture, seed_users_fixture, seed_patients_fixture, client):
        self.client = client

        # Get a user with the correct permissions
        self.ah_user = NPDAUser.objects.filter(
            organisation_employers__pz_code=ALDER_HEY_PZ_CODE,
            groups__name=test_user_audit_centre_editor_data.group_name,
        ).first()
        self.client = login_and_verify_user(self.client, self.ah_user)

        # Initialize the session
        middleware = SessionMiddleware(get_response=lambda request: None)
        request = self.client.request().wsgi_request
        middleware.process_request(request)
        request.session.save()

        # Modify the session
        session = self.client.session
        session["can_upload_csv"] = False
        session["can_complete_questionnaire"] = True
        session["pz_code"] = ALDER_HEY_PZ_CODE
        session["selected_audit_year"] = audit_dates[0].year
        session.save()

    def test_users_with_correct_permissions_can_save_patient(self):
        """
        Test that users who do not have the can_upload_csv permission cannot save a patient through the questionnaire view.
        """
        # Create a patient
        form = PatientForm(VALID_FIELDS)

        # url
        url = reverse("patient-add")

        # Post the patient data
        response = self.client.post(url, form.data)

        # Check that the patient was not saved
        assert Patient.objects.filter(nhs_number=form.data["nhs_number"]).exists() is True
        assert response.status_code == 302  # Redirects to the patient list page

    def test_users_with_correct_permissions_cannot_save_patient_in_different_audit_year(
        self,
    ):
        """
        Test that users who have the questionnaire permission cannot save a patient in a different audit year.
        """
        # Create a patient
        form = PatientForm(VALID_FIELDS)
        print(audit_dates)
        # Modify the session
        session = self.client.session
        session["selected_audit_year"] = (
            audit_dates[0].year + 2
        )  # 2 years in the future will always be a different audit year
        session.save()

        print(self.client.session["selected_audit_year"])

        # url
        url = reverse("patient-add")

        # Post the patient data
        response = self.client.post(url, form.data)

        assert response.status_code == 403
        assert Patient.objects.filter(nhs_number=form.data["nhs_number"]).exists() is False

    def test_rcpch_users_with_correct_permissions_can_still_save_patient_in_different_audit_year(
        self,
    ):
        """
        Test that RCPCH audit users who have the questionnaire permission can still save a patient in a different audit year.
        """
        # Create a patient
        form = PatientForm(VALID_FIELDS)

        # Modify the session
        session = self.client.session
        session["selected_audit_year"] = audit_dates[0].year + 1
        session.save()

        # Give the user the RCPCH audit team group
        self.ah_user.is_rcpch_audit_team_member = True
        self.ah_user.save()

        # url
        url = reverse("patient-add")

        # Post the patient data
        response = self.client.post(url, form.data)

        assert response.status_code == 302  # Redirects to the patient list page
        assert Patient.objects.filter(nhs_number=form.data["nhs_number"]).exists() is True

    def test_users_without_questionnaire_permissions_cannot_save_patient(self):
        """
        Test that users who do not have the questionnaire permission cannot save a patient through the questionnaire view.
        """
        # Modify the session
        session = self.client.session
        session["can_complete_questionnaire"] = False
        session.save()

        # Create a patient
        form = PatientForm(VALID_FIELDS)

        # url
        url = reverse("patient-add")

        # Post the patient data
        response = self.client.post(url, form.data)

        assert response.status_code == 403
        assert Patient.objects.filter(nhs_number=form.data["nhs_number"]).exists() is False

    def test_rcpch_users_without_questionnaire_permissions_can_still_save_patient(self):
        """
        Test that RCPCH audit users who do not have the questionnaire permission can still save a patient through the questionnaire view.
        (Though this is theoretical as they have the permission by default)
        """
        # Modify the session
        session = self.client.session
        session["can_complete_questionnaire"] = False
        session.save()

        # Give the user the RCPCH audit team group
        self.ah_user.is_rcpch_audit_team_member = True
        self.ah_user.save()

        # Create a patient
        form = PatientForm(VALID_FIELDS)

        # url
        url = reverse("patient-add")

        # Post the patient data
        response = self.client.post(url, form.data)

        assert response.status_code == 302
        assert Patient.objects.filter(nhs_number=form.data["nhs_number"]).exists() is True

    def test_users_with_correct_permissions_can_save_visit(self):
        """
        Test that users who do have questionnaire permission can save a visit through the questionnaire view.
        """
        # Create a patient
        patient = PatientFactory()

        form = VisitForm(data=COMPLETED_VISIT, initial={"patient": patient})

        # url
        url = reverse("visit-create", kwargs={"patient_id": patient.pk})

        # Post the patient data
        response = self.client.post(url, form.data)

        # Cannot check that the visit was saved as a visit is created in the VisitForm instance
        assert response.status_code == 200

    def test_users_with_correct_permissions_without_questionnaire_permission_cannot_save_visit(
        self,
    ):
        """
        Test that users who do have questionnaire permission can save a visit through the questionnaire view.
        """
        # Create a patient
        patient = PatientFactory()

        form = VisitForm(data=COMPLETED_VISIT, initial={"patient": patient})

        # Modify the session
        session = self.client.session
        session["can_complete_questionnaire"] = False
        session.save()

        # url
        url = reverse("visit-create", kwargs={"patient_id": patient.pk})

        # Post the patient data
        response = self.client.post(url, form.data)

        assert response.status_code == 403
        # Cannot check if the visit was not saved as a visit is created in the VisitForm instance
