# python imports
from datetime import date
import logging

# Django imports
from django.apps import apps
from django.utils import timezone
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Case, When, Max, Q, F
from django.forms import BaseForm
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView
from django.http import HttpResponse
from django.urls import reverse_lazy

# Third party imports


from project.npda.general_functions import (
    get_new_session_fields,
    get_or_update_view_preference,
    organisations_adapter,
)
from project.npda.general_functions.quarter_for_date import retrieve_quarter_for_date
from project.npda.models import NPDAUser

# RCPCH imports
from ..models import Patient
from ..forms.patient_form import PatientForm
from .mixins import CheckPDUInstanceMixin, CheckPDUListMixin, LoginAndOTPRequiredMixin

logger = logging.getLogger(__name__)


class PatientListView(
    LoginAndOTPRequiredMixin, CheckPDUListMixin, PermissionRequiredMixin, ListView
):
    permission_required = "npda.view_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    template_name = "patients.html"

    def get_queryset(self):
        """
        Return all patients with the number of errors in their visits
        Order by valid patients first, then by number of errors in visits, then by primary key
        Scope to patient only in the same organisation as the user and current audit year
        """
        pz_code = self.request.session.get("pz_code")
        filtered_patients = None
        # filter patients to the view preference of the user
        if self.request.user.view_preference == 0:
            # organisation view
            # this has been deprecated
            pass
        elif self.request.user.view_preference == 1:
            # PDU view
            filtered_patients = Q(
                submissions__paediatric_diabetes_unit__pz_code=pz_code,
            )
        elif self.request.user.view_preference == 2:
            # National view - no filter
            pass
        else:
            raise ValueError("Invalid view preference")

        patient_queryset = Patient.objects.filter(
            submissions__submission_active=True,
        )
        if filtered_patients is not None:
            patient_queryset = patient_queryset.filter(filtered_patients)

        patient_queryset = patient_queryset.annotate(
            audit_year=F("submissions__audit_year"),
            visit_error_count=Count(Case(When(visit__is_valid=False, then=1))),
            last_upload_date=Max("submissions__submission_date"),
            most_recent_visit_date=Max("visit__visit_date"),
        ).order_by("is_valid", "visit_error_count", "pk")

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
            .filter(is_valid=True, visit_error_count__lt=1)
            .count()
        )
        context["pz_code"] = self.request.session.get("pz_code")
        context["total_valid_patients"] = total_valid_patients
        context["total_invalid_patients"] = (
            Patient.objects.filter(submissions__submission_active=True).count()
            - total_valid_patients
        )
        context["index_of_first_invalid_patient"] = total_valid_patients
        context["pdu_choices"] = (
            organisations_adapter.paediatric_diabetes_units_to_populate_select_field(
                request=self.request, user_instance=self.request.user
            )
        )
        context["chosen_pdu"] = self.request.session.get("pz_code")
        return context

    def get(self, request, *args: str, **kwargs) -> HttpResponse:
        response = super().get(request, *args, **kwargs)
        if request.htmx:
            print("htmx request")
            # filter the patients to only those in the same organisation as the user
            # trigger a GET request from the patient table to update the list of patients
            # by calling the get_queryset method again with the new ods_code/pz_code stored in session
            queryset = self.get_queryset()
            context = self.get_context_data()
            context["patient_list"] = queryset

            return render(request, "partials/patient_table.html", context=context)
        return response


class PatientCreateView(
    LoginAndOTPRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    """
    Handle creation of new patient in audit - should link the patient to the current audit year and the logged in user's PDU
    """

    permission_required = "npda.add_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    form_class = PatientForm
    success_message = "New child record created was created successfully"
    success_url = reverse_lazy("patients")

    def get_context_data(self, **kwargs):
        PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")

        pz_code = self.request.session.get("pz_code")
        pdu = PaediatricDiabetesUnit.objects.get(pz_code=pz_code)
        context = super().get_context_data(**kwargs)
        context["title"] = (
            f"Add New Child to {pdu.lead_organisation_name} - {pdu.parent_name} ({pz_code})"
        )
        context["button_title"] = "Add New Child"
        context["form_method"] = "create"
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
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

        return super().form_valid(form)


class PatientUpdateView(
    LoginAndOTPRequiredMixin,
    CheckPDUInstanceMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """
    Handle update of patient in audit
    """

    permission_required = "npda.change_patient"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Patient
    form_class = PatientForm
    success_message = "New child record updated successfully"
    success_url = reverse_lazy("patients")
    Submission = apps.get_model("npda", "Submission")

    def get_context_data(self, **kwargs):
        Transfer = apps.get_model("npda", "Transfer")
        patient = Patient.objects.get(pk=self.kwargs["pk"])

        transfer = Transfer.objects.get(patient=patient)

        context = super().get_context_data(**kwargs)
        context["title"] = (
            f"Edit Child Details in {transfer.paediatric_diabetes_unit.lead_organisation_name} - {transfer.paediatric_diabetes_unit.parent_name} ({transfer.paediatric_diabetes_unit.pz_code})"
        )
        context["button_title"] = "Edit Child Details"
        context["form_method"] = "update"
        context["patient_id"] = self.kwargs["pk"]
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        patient = form.save(commit=False)
        patient.is_valid = True
        patient.errors = None
        patient.save()
        return super().form_valid(form)


class PatientDeleteView(
    LoginAndOTPRequiredMixin,
    CheckPDUInstanceMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
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
