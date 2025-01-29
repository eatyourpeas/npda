# Python imports
from typing import Any, Iterable
from datetime import date
import json

# Django imports
from django.apps import apps
from django.contrib import messages
from django.db.models import Count, Case, When, F, Value
from django.db.models.functions import Concat
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import ListView

from project.npda.views.decorators import login_and_otp_required

# RCPCH imports
from .mixins import CheckCurrentAuditYearMixin, LoginAndOTPRequiredMixin
from ..models import Submission
from ..general_functions.csv import (
    download_csv,
    download_xlsx,
    csv_parse,
)


class SubmissionsListView(
    LoginAndOTPRequiredMixin, CheckCurrentAuditYearMixin, ListView
):
    """
    The SubmissionsListView class.

    This class is used to display a list of submissions.

    Users with permisson should be able to view all submissions for the PDU & ODS code in the session for all audit years/quarters.
    Only one submission per audit year/quarter should be active.
    It is only possible to create/update/delete a submission for the current audit year/quarter.
    """

    model = apps.get_model(app_label="npda", model_name="Submission")
    template_name = "submissions_list.html"
    context_object_name = "submissions"

    def get_queryset(self) -> Iterable[Any]:
        """
        Retrieve all submissions for the current PZ code, unless view_preference is set to 2 (national view)
        """
        PaediatricDiabetesUnit = apps.get_model(
            app_label="npda", model_name="PaediatricDiabetesUnit"
        )
        pdu = PaediatricDiabetesUnit.objects.get(
            pz_code=self.request.session.get("pz_code"),
        )
        if self.request.user.view_preference == 1:
            base_queryset = self.model.objects.filter(
                paediatric_diabetes_unit=pdu,
                audit_year=self.request.session.get("selected_audit_year"),
            )
        else:
            base_queryset = self.model.objects.filter(
                audit_year=self.request.session.get("selected_audit_year")
            ).all()

        final = base_queryset.annotate(
            patient_count=Count("patients"),
            full_name_submission_by=Concat(
                "submission_by__first_name", Value(" "), "submission_by__surname"
            ),
        ).order_by(
            "audit_year",
            "-submission_active",
            "-submission_date",
        )
        
        return final

    def get_context_data(self, **kwargs: Any) -> dict:
        """
        Add data to the context.
        Includes the patient data for the active submission and the csv summary data.
        """
        context = super().get_context_data(**kwargs)
        context["pz_code"] = self.request.session.get("pz_code")
        context["selected_audit_year"] = self.request.session.get("selected_audit_year")
        Patient = apps.get_model("npda", "Patient")
        context["data"] = None  # data stores csv summary data if a submission exists
        requested_active_submission = self.object_list.filter(
            submission_active=True,
            audit_year=self.request.session.get("selected_audit_year"),
            paediatric_diabetes_unit__pz_code=self.request.session.get("pz_code"),
        ).first()  # there can be only one of these
        if requested_active_submission:
            # If a submission exists and it was created by uploading a csv, summarize the csv data
            if self.request.session.get("can_upload_csv"):
                # check if the user has permission to upload csv (not this function is not available in this brance but is in live)
                parsed_csv = csv_parse(requested_active_submission.csv_file)
                if requested_active_submission.errors:
                    deserialized_errors = json.loads(requested_active_submission.errors)
                    context["submission_errors"] = deserialized_errors
                else:
                    context["submission_errors"] = None

            # Get some summary data about the patients in the submission...
            context["patients"] = Patient.objects.filter(
                submissions=requested_active_submission
            ).annotate(
                visit_error_count=Count(Case(When(visit__is_valid=False, then=1))),
                visit_count=Count("visit"),
            )

        return context

    def get(self, request, *args, **kwargs):
        """
        Handle the HTMX GET request.
        """
        self.object_list = self.get_queryset().order_by("-submission_date")
        context = self.get_context_data(object_list=self.object_list)
        template = self.template_name

        if request.htmx:
            # If the request is an HTMX request from the PDU selector or Audit Year selector, returns the partial template
            # Otherwise, returns the full template
            # The partial template is used to update the submission history table when a new PDU is selected
            # This is done with a custom htmx trigger in the PDU selector
            template = "partials/submission_history.html"
        return render(request=request, template_name=template, context=context)

    def post(self, request, *args, **kwargs):
        """
        Handle the HTMX POST request.
        The button name "submit-data" is used to determine the action to be taken.
        If the value of "submit-data" is "delete-data", the submission is deleted.
        If the value of "submit-data" is "download-data", the original csv is downloaded.
        If the value of "submit-data" is "download-report", the commented xlsx (with validation remarks) is downloaded.
        """
        button_name = request.POST.get("submit-data")
        if button_name == "delete-data":
            # retrieve the  submission instance
            submission = Submission.objects.filter(
                pk=request.POST.get("audit_id")
            ).get()

            # check if the submission is active - if so, do not allow deletion, and return an error message
            if submission.submission_active:
                self.object_list = self.get_queryset()
                context = self.get_context_data(object_list=self.object_list)
                messages.error(
                    request,
                    "Cannot delete an active submission. Please make another submission active before deleting this one",
                )
                return render(request, self.template_name, context=context)

            # delete the patients associated with the submission
            submission.patients.all().delete()
            # then delete the submission itself
            submission.delete()

            # set the submission_active flag to True for the most recent submission
            if Submission.objects.count() > 0:
                new_first = Submission.objects.order_by("-submission_date").first()
                new_first.submission_active = True
                new_first.save()
            messages.success(request, "Cohort submission deleted successfully")

        submission = None

        if request.POST.get("audit_id"):
            submission = Submission.objects.filter(
                pk=request.POST.get("audit_id")
            ).get()
        else:
            submission = self.get_queryset().order_by("-submission_date").first()

        if button_name == "download-data":
            return download_csv(request, submission.id)

        if button_name == "download-report":
            return download_xlsx(request, submission.id)

        # POST is not supported for this view
        # Must therefore return the queryset as an obect_list and context
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list)
        return render(request, self.template_name, context=context)

    def render_to_response(self, context: dict) -> HttpResponse:
        """
        Render the response.

        :param context: The context
        :return: The response
        """
        return super().render_to_response(context)

@login_and_otp_required()
def upload_csv(request):
    return render(request, "upload_csv/file_upload.html")