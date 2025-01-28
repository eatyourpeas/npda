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
from ..general_functions import get_visit_categories, get_visit_tabs
from ..kpi_class.kpis import CalculateKPIS
from ..models import Patient, Transfer, Visit
from ...constants.visit_categories import VISIT_TABS
from .mixins import (
    CheckCanCompleteQuestionnaireMixin,
    CheckCurrentAuditYearMixin,
    CheckPDUInstanceMixin,
    CheckPDUListMixin,
    LoginAndOTPRequiredMixin,
)

# Third party imports


class PatientVisitsListView(
    LoginAndOTPRequiredMixin, CheckPDUListMixin, PermissionRequiredMixin, ListView
):
    """
    The PatientVisitsListView class.

    This class is used to display a list of visits for a patient.
    Note that it is possible to view the visits for a patient that are not part of the current audit submission as they are filtered against the audit year in the session.

    Users with permission should be able to view all visits for a patient.
    Users should NOT be able to add, edit or delete visits for a patient in a submission that is not active, or that is not the current audit year/quarter.
    """

    permission_required = "npda.view_visit"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Visit
    template_name = "visits.html"

    def get_context_data(self, **kwargs):
        patient_id = self.kwargs.get("patient_id")
        context = super(PatientVisitsListView, self).get_context_data(**kwargs)
        patient = Patient.objects.get(pk=patient_id)
        submission = patient.submissions.filter(
            submission_active=True,
            audit_year=self.request.session.get("selected_audit_year"),
        ).first()
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
        kpi_calculations_object = calculate_kpis.calculate_kpis_for_single_patient(
            patient,
            pdu,
        )

        context["kpi_calculations_object"] = kpi_calculations_object

        return context


class VisitCreateView(
    LoginAndOTPRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CheckCurrentAuditYearMixin,
    CheckCanCompleteQuestionnaireMixin,
    CreateView,
):
    permission_required = "npda.add_visit"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Visit
    form_class = VisitForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patient_id"] = self.kwargs["patient_id"]
        patient = Patient.objects.get(pk=self.kwargs["patient_id"])
        context["nhs_number"] = patient.nhs_number
        context["title"] = "Add New Visit"
        context["form_method"] = "create"
        context["button_title"] = "Add New Visit"
        # TODO MRB: make this work again
        # context["visit_tabs"] = VISIT_TABS
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
    LoginAndOTPRequiredMixin,
    CheckPDUInstanceMixin,
    PermissionRequiredMixin,
    CheckCurrentAuditYearMixin,
    CheckCanCompleteQuestionnaireMixin,
    UpdateView,
):
    permission_required = "npda.change_visit"
    permission_denied_message = "You do not have the appropriate permissions to access this page/feature. Contact your Coordinator for assistance."
    model = Visit
    form_class = VisitForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        visit_instance = Visit.objects.get(pk=self.kwargs["pk"])
        context["visit_instance"] = visit_instance
        context["visit_errors"] = [visit_instance.errors]
        context["patient_id"] = self.kwargs["patient_id"]
        context["nhs_number"] = visit_instance.patient.nhs_number
        context["visit_id"] = self.kwargs["pk"]
        context["title"] = "Edit Visit Details"
        context["button_title"] = "Edit Visit Details"
        context["form_method"] = "update"
        context["visit_tabs"] = get_visit_tabs(visit_instance)

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
    CheckCurrentAuditYearMixin,
    CheckCanCompleteQuestionnaireMixin,
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
