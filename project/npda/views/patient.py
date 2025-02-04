# python imports
import logging
import json
import datetime

# Django imports
from django.apps import apps
from django.utils import timezone
from django.contrib import messages
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Case, When, Max, Q, F, OuterRef, Exists
from django.forms import BaseForm
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView
from django.http import HttpResponse
from django.urls import reverse_lazy


# Third party imports
import nhs_number

from project.constants.leave_pdu_reasons import LEAVE_PDU_REASONS
from project.npda.general_functions import (
    organisations_adapter,
    fetch_organisation_by_ods_code,
)
from project.npda.general_functions.quarter_for_date import (
    retrieve_quarter_for_date,
)
from project.npda.models import (
    NPDAUser,
    Patient,
    Submission,
)
from project.npda.models.paediatric_diabetes_unit import PaediatricDiabetesUnit

# RCPCH imports
from ..forms.patient_form import PatientForm
from .mixins import (
    CheckCanCompleteQuestionnaireMixin,
    CheckCurrentAuditYearMixin,
    CheckPDUInstanceMixin,
    CheckPDUListMixin,
    LoginAndOTPRequiredMixin,
)
from ..general_functions.session import refresh_session_object_synchronously

logger = logging.getLogger(__name__)


class PatientListView(
    LoginAndOTPRequiredMixin,
    CheckPDUListMixin,
    PermissionRequiredMixin,
    ListView,
):
    permission_required = "npda.view_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    template_name = "patients.html"
    paginate_by = 50

    def get_sort_by(self):
        sort_by_param = self.request.GET.get("sort_by")
        sort_param = self.request.GET.get("sort")

        sort_by = None

        # Check we are sorting by a fixed set of fields rather than the full Django __ notation
        if sort_by_param in [
            "nhs_number",
            "index_of_multiple_deprivation_quintile",
            "distance_from_lead_organisation",
        ]:
            sort_by = sort_by_param

        sort_by = f"-{sort_by}" if sort_param == "desc" else sort_by

        return sort_by

    def get_queryset(self):
        patient_queryset = super().get_queryset()

        PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")

        # apply filters and annotations to the queryset
        pz_code = self.request.session.get("pz_code")
        paediatric_diabetes_unit = PaediatricDiabetesUnit.objects.get(pz_code=pz_code)
        paediatric_diabetes_unit_lead_organisation = fetch_organisation_by_ods_code(
            ods_code=paediatric_diabetes_unit.lead_organisation_ods_code
        )
        filtered_patients = Q(
            submissions__submission_active=True,
            submissions__audit_year=self.request.session.get("selected_audit_year"),
        )

        # filter by contents of the search bar
        search = self.request.GET.get("search-input")
        if search:
            search = nhs_number.standardise_format(search) or search
            filtered_patients &= Q(
                Q(nhs_number__icontains=search) | Q(pk__icontains=search)
            )

        # filter patients to the view preference of the user
        if self.request.user.view_preference == 1:
            # PDU view
            filtered_patients &= Q(
                submissions__paediatric_diabetes_unit__pz_code=pz_code
            )

        patient_queryset = patient_queryset.filter(filtered_patients)

        patient_queryset = patient_queryset.annotate(
            audit_year=F("submissions__audit_year"),
            visit_error_count=Count(Case(When(visit__is_valid=False, then=1))),
            last_upload_date=Max("submissions__submission_date"),
            most_recent_visit_date=Max("visit__visit_date"),
            distance_from_lead_organisation=Distance(
                "location_wgs84",
                Point(
                    paediatric_diabetes_unit_lead_organisation["longitude"],
                    paediatric_diabetes_unit_lead_organisation["latitude"],
                    srid=4326,
                ),
            ),
        )

        sort_by = self.get_sort_by()

        if sort_by:
            patient_queryset = patient_queryset.order_by(sort_by)
        else:
            patient_queryset = patient_queryset.order_by(
                "is_valid", "-visit_error_count"
            )

        return patient_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pz_code = self.request.session.get("pz_code")
        selected_audit_year = self.request.session.get("selected_audit_year")

        pdu = PaediatricDiabetesUnit.objects.get(pz_code=pz_code) if pz_code else None
        context["pdu"] = pdu

        submission = None
        submission_error_count = 0

        # TODO MRB: this should probably be a method on the Submission model?
        #           https://github.com/rcpch/national-paediatric-diabetes-audit/issues/533
        if pz_code and selected_audit_year:
            submission = (
                Submission.objects.filter(
                    paediatric_diabetes_unit__pz_code=pz_code,
                    audit_year=selected_audit_year,
                )
                .order_by("-submission_date")
                .first()
            )

            if submission and submission.errors:
                submission_errors = json.loads(submission.errors)

                error_count = 0
                for errors_for_visit in submission_errors.values():
                    for errors_for_field in errors_for_visit.values():
                        submission_error_count += len(errors_for_field)

        context["submission"] = submission
        context["submission_valid_count"] = (
            context["paginator"].count - submission_error_count
        )
        context["submission_error_count"] = submission_error_count

        context["pz_code"] = pz_code
        context["selected_audit_year"] = selected_audit_year or "None"
        context["pdu_choices"] = (
            organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
                requesting_user=self.request.user,
                user_instance=self.request.user,
            )
        )
        context["chosen_pdu"] = pz_code
        context["current_page"] = self.request.GET.get("page", 1)
        context["sort_by"] = self.get_sort_by()

        # Add extra fields to the patient that we can't add to the query. This is ok because the queryset will be max the page size.
        error_count_in_page = 0
        valid_count_in_page = 0

        for patient in context["page_obj"]:
            # Signpost the latest quarter
            if patient.most_recent_visit_date is not None:
                patient.latest_quarter = retrieve_quarter_for_date(
                    patient.most_recent_visit_date
                )

            # Highlight the separation between patients with errors and those without
            # unless we are sorting by a particular field in which case errors appear mixed
            if not context["sort_by"]:
                if not patient.is_valid or patient.visit_error_count > 0:
                    if error_count_in_page == 0:
                        patient.is_first_error = True

                    error_count_in_page += 1

                if patient.is_valid and patient.visit_error_count == 0:
                    if valid_count_in_page == 0:
                        patient.is_first_valid = True

                    valid_count_in_page += 1

        context["error_count_in_page"] = error_count_in_page
        context["valid_count_in_page"] = valid_count_in_page

        return context

    def get(self, request, *args: str, **kwargs) -> HttpResponse:
        response = super().get(request, *args, **kwargs)

        if request.htmx:
            return render(
                request, "partials/patient_table.html", context=self.get_context_data()
            )

        return response


class PatientCreateView(
    LoginAndOTPRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CheckCurrentAuditYearMixin,
    CheckCanCompleteQuestionnaireMixin,
    CreateView,
):
    """
    Handle creation of new patient in audit - should link the patient to the current audit year and the logged in user's PDU
    Note that patients can only be created in the current audit year
    """

    permission_required = "npda.add_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    form_class = PatientForm
    success_message = "New child record created successfully"
    success_url = reverse_lazy("patients")

    def get_context_data(self, **kwargs):
        PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")
        pz_code = self.request.session.get("pz_code")
        pdu = PaediatricDiabetesUnit.objects.get(pz_code=pz_code)
        context = super().get_context_data(**kwargs)
        title = f"Add New Child to {pdu.lead_organisation_name}  ({pz_code})"
        if (
            pdu.parent_name is not None
        ):  # if the PDU has a parent, include the parent name in the title
            title = f"Add New Child to {pdu.lead_organisation_name} - {pdu.parent_name} ({pz_code})"
        context["title"] = title
        context["button_title"] = "Add New Child"
        context["form_method"] = "create"
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        if self.request.session.get("can_complete_questionnaire"):
            # the Patient record is therefore valid
            patient = form.save(commit=False)
            patient.is_valid = True
            patient.errors = None
            patient.save()

            # add the PDU to the patient record
            # get or create the paediatric diabetes unit object
            PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")
            paediatric_diabetes_unit = PaediatricDiabetesUnit.objects.get(
                pz_code=self.request.session.get("pz_code"),
            )

            Transfer = apps.get_model("npda", "Transfer")
            if Transfer.objects.filter(patient=patient).exists():
                # the patient is being transferred from another PDU. Update the previous_pz_code field
                transfer = Transfer.objects.get(patient=patient)
                transfer.previous_pz_code = transfer.paediatric_diabetes_unit.pz_code
                transfer.paediatric_diabetes_unit = paediatric_diabetes_unit
                transfer.date_leaving_service = (
                    form.cleaned_data.get("date_leaving_service"),
                )
                transfer.reason_leaving_service = (
                    form.cleaned_data.get("reason_leaving_service"),
                )
                transfer.save()
            else:
                Transfer.objects.create(
                    paediatric_diabetes_unit=paediatric_diabetes_unit,
                    patient=patient,
                    date_leaving_service=None,
                    reason_leaving_service=None,
                )
            # add patient to the latest audit year and the logged in user's PDU
            # the form is initialised with the current audit year

            Submission = apps.get_model("npda", "Submission")
            submission, created = Submission.objects.update_or_create(
                audit_year=self.request.session["selected_audit_year"],
                paediatric_diabetes_unit=paediatric_diabetes_unit,
                submission_active=True,
                defaults={
                    "submission_by": NPDAUser.objects.get(pk=self.request.user.pk),
                    "submission_by": NPDAUser.objects.get(pk=self.request.user.pk),
                    "submission_date": timezone.now(),
                },
            )
            submission.patients.add(patient)
            submission.save()
            # update the session
            refresh_session_object_synchronously(
                request=self.request,
                user=self.request.user,
                pz_code=self.request.session.get("pz_code"),
            )

        else:
            logger.error(
                f"User {self.request.user} attempted to add a new patient to the audit, but the submission for {self.request.session['pz_code']} is done through csv upload."
            )
            messages.error(
                self.request,
                "The submission for this PDU is done through csv upload and data cannot be added or edited through the questionnaire. If you need to edit the submission directly please contact the NPDA team for assistance.",
            )

        return super().form_valid(form)


class PatientUpdateView(
    LoginAndOTPRequiredMixin,
    CheckPDUInstanceMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CheckCurrentAuditYearMixin,
    CheckCanCompleteQuestionnaireMixin,
    UpdateView,
):
    """
    Handle update of patient in audit
    Note patients can only be updated in the current audit year
    """

    permission_required = "npda.change_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    form_class = PatientForm
    success_message = "New child record updated successfully"
    success_url = reverse_lazy("patients")
    Submission = apps.get_model("npda", "Submission")
    PatientSubmission = apps.get_model("npda", "PatientSubmission")

    def get_context_data(self, **kwargs):
        Transfer = apps.get_model("npda", "Transfer")
        pz_code = self.request.session.get("pz_code")
        patient = Patient.objects.get(pk=self.kwargs["pk"])
        transfer = Transfer.objects.get(patient=patient)
        context = super().get_context_data(**kwargs)
        PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")
        pdu = PaediatricDiabetesUnit.objects.get(pz_code=pz_code)
        title = f"Edit Child Details in {pdu.lead_organisation_name}  ({pz_code})"
        if (
            transfer.paediatric_diabetes_unit.parent_name is not None
        ):  # if the PDU has a parent, include the parent name in the title
            title = f"Add New Child to {transfer.paediatric_diabetes_unit.lead_organisation_name} - {transfer.paediatric_diabetes_unit.parent_name} ({pz_code})"
        context["title"] = title
        context["button_title"] = "Edit Child Details"
        context["form_method"] = "update"
        context["patient_id"] = self.kwargs["pk"]
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        patient = form.save(commit=False)
        patient.is_valid = True
        patient.errors = None
        # TODO MRB: this calls patient.save twice. super.form_valid calls it too (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/335)
        patient.save()
        return super().form_valid(form)


class PatientDeleteView(
    LoginAndOTPRequiredMixin,
    CheckPDUInstanceMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CheckCurrentAuditYearMixin,
    CheckCanCompleteQuestionnaireMixin,
    DeleteView,
):
    """
    Handle deletion of child from audit
    """

    permission_required = "npda.delete_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    success_message = "Child removed from database"
    success_url = reverse_lazy("patients")
