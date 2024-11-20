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
from project.npda.models import NPDAUser, Submission
from project.npda.models import Patient
from project.npda.tests.utils import login_and_verify_user
from project.npda.general_functions import audit_period

logger = logging.getLogger(__name__)

ALDER_HEY_PZ_CODE = "PZ074"
ALDER_HEY_ODS_CODE = "RBS25"

GOSH_PZ_CODE = "PZ196"
GOSH_ODS_CODE = "RP401"

audit_dates = audit_period.get_audit_period_for_date(date.today())


@pytest.mark.django_db
def test_questionnaire_view_users_without_permission_cannot_save_patient(
    seed_groups_fixture,
    seed_users_fixture,
    seed_patients_fixture,
    client,
):
    """
    Test that users who do not have the can_upload_csv permission cannot save a patient through the questionnaire view.
    """

    def get_response(request):
        return None

    # Get a user
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE,
    ).first()
    client = login_and_verify_user(client, ah_user)

    # set the session
    # Initialize the session
    middleware = SessionMiddleware(get_response=get_response)
    request = client.request().wsgi_request
    middleware.process_request(request)
    request.session.save()

    # Modify the session
    session = client.session
    session["can_upload_csv"] = False
    session["can_complete_questionnaire"] = True
    session["pz_code"] = ALDER_HEY_PZ_CODE
    session["selected_audit_year"] = audit_dates[0].year
    session.save()

    # Create a patient
    form = PatientForm(VALID_FIELDS)

    # url
    url = reverse("patient-add")

    # Post the patient data
    response = client.post(url, form.data)

    # Check that the patient was not saved
    assert Patient.objects.filter(nhs_number=form.data["nhs_number"]).exists() is True
    assert response.status_code == 200
