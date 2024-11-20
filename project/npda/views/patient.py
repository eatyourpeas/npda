# python imports
from datetime import date
import logging

# Django imports
from django.apps import apps
from django.utils import timezone
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Case, When, Max, Q, F
from django.forms import BaseForm, ValidationError
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView
from django.http import HttpResponse
from django.urls import reverse_lazy

# Third party imports


from project.npda.general_functions import (
    organisations_adapter,
)
from project.npda.general_functions.quarter_for_date import (
    retrieve_quarter_for_date,
)
from project.npda.models import NPDAUser

# RCPCH imports
from ..models import Patient
from ..forms.patient_form import PatientForm
from .mixins import (
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

    def get_queryset(self):
        """
        Return all patients with the number of errors in their visits
        Order by valid patients first, then by number of errors in visits, then by primary key
        Scope to patient only in the same organisation as the user and current audit year
        """
        patient_queryset = super().get_queryset()
        # sort the queryset by the user'selection
        sort_by = self.request.GET.get("sort_by", "pk")  # Default sort by npda_id
        sort = self.request.GET.get("sort", "asc")  # Default sort by ascending order
        if sort_by in ["pk", "nhs_number"]:
            if sort == "asc":
                sort_by = sort_by
            else:
                sort_by = f"-{sort_by}"

        # apply filters and annotations to the queryset
        pz_code = self.request.session.get("pz_code")
        filtered_patients = Q(
            submissions__submission_active=True,
            submissions__audit_year=self.request.session.get("selected_audit_year"),
        )
        # filter by contents of the search bar
        search = self.request.GET.get("search-input")
        if search:
            filtered_patients &= Q(
                Q(nhs_number__icontains=search) | Q(pk__icontains=search)
            )
        # filter patients to the view preference of the user
        if self.request.user.view_preference == 1:
            # PDU view
            filtered_patients &= Q(
                submissions__paediatric_diabetes_unit__pz_code=pz_code
            )

        patient_queryset = (
            patient_queryset.filter(filtered_patients)
            .annotate(
                audit_year=F("submissions__audit_year"),
                visit_error_count=Count(Case(When(visit__is_valid=False, then=1))),
                last_upload_date=Max("submissions__submission_date"),
                most_recent_visit_date=Max("visit__visit_date"),
            )
            .order_by("is_valid", "visit_error_count", sort_by)
        )

        # add another annotation to the queryset to signpost the latest quarter
        # This does involve iterating over the queryset, but it is necessary to add the latest_quarter attribute to each object
        # as django does not support annotations with custom functions, at least, not without rewriting it in SQL or using the Func class
        # and the queryset is not large
        for obj in patient_queryset:
            if obj.most_recent_visit_date is not None:
                obj.latest_quarter = retrieve_quarter_for_date(
                    obj.most_recent_visit_date
                )
            else:
                obj.latest_quarter = None

        return patient_queryset

    def get_context_data(self, **kwargs):
        """
        Add total number of valid and invalid patients to the context, as well as the index of the first invalid patient in the list
        Include the number of errors in each patient's visits
        Pass the context to the template
        """
        context = super().get_context_data(**kwargs)
        total_valid_patients = (
            Patient.objects.filter(submissions__submission_active=True)
            .annotate(
                visit_error_count=Count(Case(When(visit__is_valid=False, then=1))),
            )
            .order_by("is_valid", "visit_error_count", "pk")
            .filter(visit__is_valid=True, visit_error_count__lt=1)
            .count()
        )
        context["pz_code"] = self.request.session.get("pz_code")
        context["total_valid_patients"] = total_valid_patients
        context["total_invalid_patients"] = (
            Patient.objects.filter(submissions__submission_active=True).count()
            - total_valid_patients
        )
        context["index_of_first_invalid_patient"] = total_valid_patients + 1
        context["pdu_choices"] = (
            organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
                requesting_user=self.request.user,
                user_instance=self.request.user,
            )
        )
        context["chosen_pdu"] = self.request.session.get("pz_code")
        # Add current page and sorting parameters to the context
        context["current_page"] = self.request.GET.get("page", 1)
        context["sort_by"] = self.request.GET.get("sort_by", "pk")
        return context

    def get(self, request, *args: str, **kwargs) -> HttpResponse:
        response = super().get(request, *args, **kwargs)
        if request.htmx:
            # filter the patients to only those in the same organisation as the user
            # trigger a GET request from the patient table to update the list of patients
            # by calling the get_queryset method again with the new ods_code/pz_code stored in session
            queryset = self.get_queryset()
            context = self.get_context_data()
            # Paginate the queryset
            page_size = self.get_paginate_by(queryset)
            page_number = request.GET.get("page", 1)
            paginator, page, queryset, is_paginated = self.paginate_queryset(
                queryset, page_size
            )

            # Update the context with the paginated queryset and pagination information
            context = self.get_context_data()
            context["patient_list"] = queryset
            context["paginator"] = paginator
            context["page_obj"] = page
            context["is_paginated"] = is_paginated
            context["patient_list"] = queryset

            return render(request, "partials/patient_table.html", context=context)
        return response


class PatientCreateView(
    LoginAndOTPRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
    CheckCurrentAuditYearMixin,
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
                audit_year=date.today().year,
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
    UpdateView,
    CheckCurrentAuditYearMixin,
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
    DeleteView,
    CheckCurrentAuditYearMixin,
):
    """
    Handle deletion of child from audit
    """

    permission_required = "npda.delete_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    success_message = "Child removed from database"
    success_url = reverse_lazy("patients")
