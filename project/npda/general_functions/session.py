from asgiref.sync import sync_to_async
from datetime import datetime
import logging

from django.core.exceptions import PermissionDenied
from django.apps import apps

# NPDA Imports
from project.npda.general_functions import (
    organisations_adapter,
)

logger = logging.getLogger(__name__)


def create_session_object(user):
    """
    Create a session object for the user, based on their permissions.
    This is called on login, and is used to filter the data the user can see.
    """

    OrganisationEmployer = apps.get_model("npda", "OrganisationEmployer")
    Submission = apps.get_model("npda", "Submission")
    primary_organisation = OrganisationEmployer.objects.filter(
        npda_user=user, is_primary_employer=True
    ).get()
    pz_code = primary_organisation.paediatric_diabetes_unit.pz_code
    pdu_choices = (
        organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
            requesting_user=user, user_instance=None
        )
    )

    can_upload_csv = True
    can_complete_questionnaire = True

    if Submission.objects.filter(
        paediatric_diabetes_unit=primary_organisation.paediatric_diabetes_unit,
        submission_active=True,
        audit_year=datetime.now().year,
    ).exists():
        # a submission exists for this PDU for this year
        submission = Submission.objects.filter(
            paediatric_diabetes_unit=primary_organisation.paediatric_diabetes_unit,
            submission_active=True,
            audit_year=datetime.now().year,
        ).get()
        if submission.csv_file and submission.csv_file.name:
            can_upload_csv = True
            can_complete_questionnaire = False
        else:
            can_upload_csv = False
            can_complete_questionnaire = True
    else:
        can_upload_csv = True
        can_complete_questionnaire = True

    session = {
        "pz_code": pz_code,
        "pdu_choices": list(pdu_choices),
        "can_upload_csv": can_upload_csv,
        "can_complete_questionnaire": can_complete_questionnaire,
    }

    return session


def get_new_session_fields(user, pz_code):
    """
    Get the new session fields for the user, based on the PZ code they have selected.
    If they are a member of the RCPCH audit team, they can see all organisations and they can upload CSVs as well as complete the questionnaire.
    If they are a member of the organisation, they can see their own organisation and they can either upload CSVs or complete the questionnaire
    until they have chosen one option or the other, after which they can only do one.
    """
    ret = {}

    Submission = apps.get_model("npda", "Submission")
    can_upload_csv = True
    can_complete_questionnaire = True

    if pz_code:
        can_see_organisations = (
            user.is_rcpch_audit_team_member
            or user.organisation_employers.filter(pz_code=pz_code).exists()
        )

        if not can_see_organisations:
            logger.warning(
                f"User {user} requested organisation {pz_code} they cannot see"
            )
            raise PermissionDenied()

        if Submission.objects.filter(
            paediatric_diabetes_unit__pz_code=pz_code,
            submission_active=True,
            audit_year=datetime.now().year,
        ).exists():
            # a submission exists for this PDU for this year
            submission = Submission.objects.filter(
                paediatric_diabetes_unit__pz_code=pz_code,
                submission_active=True,
                audit_year=datetime.now().year,
            ).get()

            if submission.csv_file and submission.csv_file.name:
                can_upload_csv = True
                can_complete_questionnaire = (
                    False
                    if not (user.is_rcpch_audit_team_member or user.is_superuser)
                    else True
                )
            else:
                can_upload_csv = (
                    False
                    if not (user.is_rcpch_audit_team_member or user.is_superuser)
                    else True
                )
                can_complete_questionnaire = True

        ret["pz_code"] = pz_code
        ret["pdu_choices"] = list(
            organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
                requesting_user=user, user_instance=None
            )
        )
        ret["can_upload_csv"] = can_upload_csv
        ret["can_complete_questionnaire"] = can_complete_questionnaire

    return ret


async def refresh_session_object_asynchronously(request, user, pz_code):
    """
    Refresh the session object and save the new fields.
    """
    session = await sync_to_async(get_new_session_fields)(user, pz_code)
    request.session.update(session)
    request.session.modified = True


def refresh_session_object_synchronously(request, user, pz_code):
    """
    Refresh the session object and save the new fields.
    """
    session = get_new_session_fields(user, pz_code)
    request.session.update(session)
    request.session.modified = True
