# python imports
import datetime

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.forms import BaseModelForm
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

# RCPCH imports
from ..forms.visit_form import VisitForm
from ..general_functions import get_visit_categories
from ..kpi_class.kpis import CalculateKPIS
from ..models import Patient, Transfer, Visit
from .mixins import CheckPDUInstanceMixin, CheckPDUListMixin, LoginAndOTPRequiredMixin

# Third party imports


class PatientVisitsListView(
    LoginAndOTPRequiredMixin, CheckPDUListMixin, PermissionRequiredMixin, ListView
):
    permission_required = "npda.view_visit"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Visit
    template_name = "visits.html"

    def get_context_data(self, **kwargs):
        patient_id = self.kwargs.get("patient_id")
        context = super(PatientVisitsListView, self).get_context_data(**kwargs)
        patient = Patient.objects.get(pk=patient_id)
        submission = patient.submissions.filter(submission_active=True).first()
        visits = Visit.objects.filter(patient=patient).order_by("is_valid", "id")
        calculated_visits = []
        for visit in visits:
            visit_categories = get_visit_categories(visit)
            calculated_visits.append({"visit": visit, "categories": visit_categories})
        context["visits"] = calculated_visits
        context["patient"] = patient
        context["submission"] = submission

        # calculate the KPIs for this patient
        pdu = (
            Transfer.objects.filter(patient=patient, date_leaving_service__isnull=True)
            .first()
            .paediatric_diabetes_unit
        )
        # get the PDU for this patient - this is the PDU that the patient is currently under.
        # If the patient has left the PDU, the date_leaving_service will be set and it will be possible to view KPIs for the PDU up until transfer,
        # if this happened during the audit period. This is TODO

        calculate_kpis = CalculateKPIS(
            calculation_date=datetime.date.today(), return_pt_querysets=False
        )
        # Calculate the KPIs for this patient, returning only subset relevant
        # for a single patient's calculation
        kpi_calculations_object = (
            calculate_kpis.calculate_kpis_for_single_patient(
                patient,
                pdu,
            )
        )

        context["kpi_calculations_object"] = kpi_calculations_object

        return context


class VisitCreateView(
    LoginAndOTPRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    permission_required = "npda.add_visit"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Visit
    form_class = VisitForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patient_id"] = self.kwargs["patient_id"]
        context["title"] = "Add New Visit"
        context["form_method"] = "create"
        context["button_title"] = "Add New Visit"
        return context

    def get_success_url(self):
        messages.add_message(
            self.request, messages.SUCCESS, "New visit added successfully"
        )
        return reverse(
            "patient_visits", kwargs={"patient_id": self.kwargs["patient_id"]}
        )

    def get_initial(self):
        initial = super().get_initial()
        patient = Patient.objects.get(pk=self.kwargs["patient_id"])
        initial["patient"] = patient
        return initial

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.patient_id = self.kwargs["patient_id"]
        super(VisitCreateView, self).form_valid(form)
        return HttpResponseRedirect(self.get_success_url())


class VisitUpdateView(
    LoginAndOTPRequiredMixin, CheckPDUInstanceMixin, PermissionRequiredMixin, UpdateView
):
    permission_required = "npda.change_visit"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Visit
    form_class = VisitForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        visit_instance = Visit.objects.get(pk=self.kwargs["pk"])
        visit_categories = get_visit_categories(visit_instance)
        context["visit_instance"] = visit_instance
        context["visit_errors"] = [visit_instance.errors]
        context["patient_id"] = self.kwargs["patient_id"]
        context["visit_id"] = self.kwargs["pk"]
        context["title"] = "Edit Visit Details"
        context["button_title"] = "Edit Visit Details"
        context["form_method"] = "update"
        context["visit_categories"] = visit_categories
        context["routine_measurements_categories"] = [
            "Measurements",
            "HBA1c",
            "Treatment",
            "CGM",
            "BP",
        ]
        context["annual_review_categories"] = [
            "Foot Care",
            "DECS",
            "ACR",
            "Cholesterol",
            "Thyroid",
            "Coeliac",
            "Psychology",
            "Smoking",
            "Dietician",
            "Sick Day Rules",
            "Immunisation (flu)",
        ]
        categories_with_errors = []
        categories_without_errors = []
        routine_measurements_categories_with_errors = []
        annual_review_categories_with_errors = []
        for category in visit_categories:
            if category["has_error"] == False:
                categories_without_errors.append(category["category"])
            else:
                categories_with_errors.append(category["category"])
                if category["category"] in context["routine_measurements_categories"]:
                    routine_measurements_categories_with_errors.append(
                        category["category"]
                    )
                elif category["category"] in context["annual_review_categories"]:
                    annual_review_categories_with_errors.append(category["category"])
        context["routine_measurements_categories_with_errors"] = (
            routine_measurements_categories_with_errors
        )
        context["annual_review_categories_with_errors"] = (
            annual_review_categories_with_errors
        )
        context["categories_with_errors"] = categories_with_errors
        context["categories_without_errors"] = categories_without_errors

        return context

    def get_success_url(self):
        messages.add_message(
            self.request, messages.SUCCESS, "Visit edited successfully"
        )
        return reverse(
            "patient_visits", kwargs={"patient_id": self.kwargs["patient_id"]}
        )

    def get_initial(self):
        initial = super().get_initial()
        patient = Patient.objects.get(pk=self.kwargs["patient_id"])
        initial["patient"] = patient
        return initial

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        visit = form.save(commit=True)
        visit.errors = None
        visit.is_valid = True
        visit.save(update_fields=["errors", "is_valid"])
        context = {"patient_id": self.kwargs["patient_id"]}
        messages.add_message(
            self.request, messages.SUCCESS, "Visit edited successfully"
        )
        return HttpResponseRedirect(
            redirect_to=reverse("patient_visits", kwargs=context)
        )


class VisitDeleteView(
    LoginAndOTPRequiredMixin,
    CheckPDUInstanceMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    permission_required = "npda.delete_visit"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Visit
    success_url = reverse_lazy("patient_visits")
    success_message = "Visit removed successfully"

    def get_success_url(self):
        messages.add_message(
            self.request, messages.SUCCESS, "Visit edited successfully"
        )
        return reverse(
            "patient_visits", kwargs={"patient_id": self.kwargs["patient_id"]}
        )
