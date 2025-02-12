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
        if submission.csv_file:
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


def refresh_session_object_synchronously(request, pz_code=None, audit_year=None):
    session = {}

    Submission = apps.get_model("npda", "Submission")
    PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")

    can_upload_csv = True
    can_complete_questionnaire = True

    pz_code = pz_code or request.session.get("pz_code")

    audit_years = SUPPORTED_AUDIT_YEARS
    audit_year = audit_year or request.session.get("selected_audit_year")

    session["audit_years"] = audit_years
    session["selected_audit_year"] = audit_year

    if pz_code:
        user = request.user

        can_see_organisations = (
            user.is_rcpch_audit_team_member
            or user.organisation_employers.filter(pz_code=pz_code).exists()
        )

        if not can_see_organisations:
            logger.warning(
                f"User {user} requested organisation {pz_code} they cannot see"
            )
            raise PermissionDenied()

        session["pz_code"] = pz_code
        session["lead_organisation"] = PaediatricDiabetesUnit.objects.get(
            pz_code=pz_code
        ).lead_organisation_name
        session["pdu_choices"] = list(
            organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
                requesting_user=user, user_instance=None
            )
        )

    session |= get_submission_actions(pz_code, audit_year)

    request.session.update(session)
    request.session.modified = True
