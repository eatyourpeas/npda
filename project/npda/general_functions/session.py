from asgiref.sync import sync_to_async
import logging

from django.core.exceptions import PermissionDenied
from django.apps import apps

# NPDA Imports
from project.npda.general_functions import (
    organisations_adapter,
    get_audit_period_for_date,
    get_current_audit_year,
    SUPPORTED_AUDIT_YEARS,
)

logger = logging.getLogger(__name__)


def get_submission_actions(pz_code, audit_year):
    Submission = apps.get_model("npda", "Submission")

    submission = Submission.objects.filter(
        paediatric_diabetes_unit__pz_code=pz_code,
        submission_active=True,
        audit_year=audit_year,
    ).first()

    can_complete_questionnaire = True
    can_upload_csv = True

    if submission:
        if submission.csv_file and submission.csv_file.name:
            can_upload_csv = True
            can_complete_questionnaire = False
        else:
            can_upload_csv = False
            can_complete_questionnaire = True

    return {
        "can_upload_csv": can_upload_csv,
        "can_complete_questionnaire": can_complete_questionnaire,
    }


def create_session_object(user):
    """
    Create a session object for the user, based on their permissions.
    This is called on login, and is used to filter the data the user can see.
    """

    OrganisationEmployer = apps.get_model("npda", "OrganisationEmployer")
    primary_organisation = OrganisationEmployer.objects.filter(
        npda_user=user, is_primary_employer=True
    ).get()
    pz_code = primary_organisation.paediatric_diabetes_unit.pz_code
    pdu_choices = (
        organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
            requesting_user=user, user_instance=None
        )
    )

    audit_year = get_current_audit_year()
    submission_actions = get_submission_actions(pz_code, audit_year)

    session = {
        "pz_code": pz_code,
        "lead_organisation": primary_organisation.paediatric_diabetes_unit.lead_organisation_name,
        "pdu_choices": list(pdu_choices),
        "selected_audit_year": audit_year,
        "audit_years": SUPPORTED_AUDIT_YEARS,
    } | submission_actions

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
    PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")
    can_upload_csv = True
    can_complete_questionnaire = True

    audit_year = get_current_audit_year()

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

        ret["pz_code"] = pz_code
        ret["lead_organisation"] = PaediatricDiabetesUnit.objects.get(
            pz_code=pz_code
        ).lead_organisation_name
        ret["pdu_choices"] = list(
            organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
                requesting_user=user, user_instance=None
            )
        )

        ret |= get_submission_actions(pz_code, audit_year)

    return ret


def refresh_audit_years_in_session(request, selected_audit_year):
    """
    Refresh the audit years in the session object.
    """
    audit_years = SUPPORTED_AUDIT_YEARS
    request.session["audit_years"] = audit_years
    request.session["selected_audit_year"] = selected_audit_year
    request.session.modified = True


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
