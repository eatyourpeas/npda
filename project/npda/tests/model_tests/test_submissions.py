"""
This file contains tests for the submissions model and views.

Model classes tested:
- Only one submissions for a PDU & ODS code in the session for a given audit year/quarter should be active

View classes tested:
 -  SubmissionsListView GET request should return all submissions for the PDU & ODS code in the session for all audit years/quarters
 -  SubmissionsListView GET request should NOT return the active submissions for a PDU & ODS code not in the session for all audit years/quarters
- SubmissionsListView POST request with param "submit-data" of value "delete-data" should delete the submission for the PDU & ODS code in the session
- SubmissionsListView POST request with param "submit-data" of value "delete-data" should NOT delete the submission for a different PDU & ODS code to that in the session
- SubmissionsListView POST request with param "submit-data" of value "delete-data" should NOT delete the submission for the PDU & ODS code in the session if the submission is not active
"""

from http import HTTPStatus
import logging
from datetime import date

# Python imports
import pytest

# 3rd party imports
from django.urls import reverse
from django.utils import timezone

from project.constants.user import RCPCH_AUDIT_TEAM

# NPDA imports
from project.npda.models import NPDAUser, Submission
from project.npda.tests.utils import login_and_verify_user
from project.npda.tests.factories import (
    PatientFactory,
    PaediatricsDiabetesUnitFactory,
    NPDAUserFactory,
)
from project.npda.general_functions import audit_period

logger = logging.getLogger(__name__)

ALDER_HEY_PZ_CODE = "PZ074"
ALDER_HEY_ODS_CODE = "RBS25"

GOSH_PZ_CODE = "PZ196"
GOSH_ODS_CODE = "RP401"

audit_dates = audit_period.get_audit_period_for_date(date.today())


@pytest.mark.django_db
def test_npda_user_can_create_submission(
    seed_groups_fixture,
    seed_patients_fixture,
    seed_users_fixture,
    client,
):
    """Test NPDAUser can create a submission for their PDU code."""

    # Get Alder Hey user from fixture
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()

    # Login as Alder Hey user

    client = login_and_verify_user(client, ah_user)

    # Get Alder Hey PDU
    pdu = PaediatricsDiabetesUnitFactory(pz_code=ALDER_HEY_PZ_CODE)

    # Create some patients
    patients = PatientFactory.create_batch(5)

    # Create a submission
    new_submission = Submission.objects.create(
        paediatric_diabetes_unit=pdu,
        audit_year=audit_dates[0].year,
        submission_date=timezone.now(),
        submission_by=ah_user,  # user is the user who is logged in. Passed in as a parameter
        submission_active=True,
    )

    # Add patients to submission
    new_submission.patients.add(*patients)

    # Check submission was created
    assert new_submission is not None
    assert new_submission in Submission.objects.all()
    # assert new_submission in ah_user.submissions.all()
    assert new_submission in pdu.pdu_submissions.all()
    assert new_submission.patients.count() == 5


@pytest.mark.django_db
def test_npda_user_cannot_submit_same_patient_twice_within_the_same_submission(
    seed_groups_fixture,
    seed_patients_fixture,
    seed_users_fixture,
    client,
):
    """Test NPDAUser cannot submit the same patient twice in the same submission."""

    # Get Alder Hey user from fixture
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()

    # Login as Alder Hey user
    client = login_and_verify_user(client, ah_user)

    # Get Alder Hey PDU
    pdu = PaediatricsDiabetesUnitFactory(pz_code=ALDER_HEY_PZ_CODE)

    # Create a submission
    new_submission = Submission.objects.create(
        paediatric_diabetes_unit=pdu,
        audit_year=audit_dates[0].year,
        submission_date=timezone.now(),
        submission_by=ah_user,  # user is the user who is logged in. Passed in as a parameter
        submission_active=True,
    )

    submission_last_audit_year = Submission.objects.create(
        paediatric_diabetes_unit=pdu,
        audit_year=audit_dates[0].year - 1,
        submission_date=timezone.now(),
        submission_by=ah_user,  # user is the user who is logged in. Passed in as a parameter
        submission_active=True,
    )

    # Create a patient
    patient = PatientFactory()

    # Add patient to previous year's submission
    submission_last_audit_year.patients.add(patient)

    # Add patient to submission
    new_submission.patients.add(patient)

    # Try to add the same patient to this year's submission a second time
    new_submission.patients.add(patient)

    # Check patient was not added to submission twice
    assert new_submission.patients.count() == 1
    assert patient in new_submission.patients.all()
    assert new_submission.patients.filter(pk=patient.pk).count() == 1
    assert (  # There should be only one submission for the patient in this audit year and PDU
        Submission.objects.filter(
            audit_year=audit_dates[0].year, paediatric_diabetes_unit=pdu
        ).count()
        == 1
    )
    # This patient should be in the previous year's submission as well as this year's submission
    assert Submission.objects.filter(paediatric_diabetes_unit=pdu).count() == 2


@pytest.xfail.django_db
def test_submission_moves_when_patient_transfers(
    seed_groups_fixture,
    seed_patients_fixture,
    seed_users_fixture,
    client,
):
    """Test that a patient is removed from the old submission and added to the new submission when they transfer."""

    # Get Alder Hey user from fixture
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()

    # Login as Alder Hey user
    client = login_and_verify_user(client, ah_user)

    # Get Alder Hey PDU
    pdu = PaediatricsDiabetesUnitFactory(pz_code=ALDER_HEY_PZ_CODE)

    # Create a submission
    new_submission = Submission.objects.create(
        paediatric_diabetes_unit=pdu,
        audit_year=audit_dates[0].year,
        submission_date=timezone.now(),
        submission_by=ah_user,  # user is the user who is logged in. Passed in as a parameter
        submission_active=True,
    )

    # Create a patient
    patient = PatientFactory()

    # Add patient to submission
    new_submission.patients.add(patient)

    # Check patient was added to submission
    assert new_submission.patients.count() == 1
    assert patient in new_submission.patients.all()

    # transfer patient to another PDU
    gosh_pdu = PaediatricsDiabetesUnitFactory(pz_code=GOSH_PZ_CODE)

    patient.transfer.date_leaving_service = date.today()
    patient.transfer.reason_leaving_service = 1
    patient.transfer.previous_pz_code = ALDER_HEY_PZ_CODE
    patient.transfer.paediatric_diabetes_unit = gosh_pdu

    patient.transfer.save()

    #  Check Alder Hey submission is empty
