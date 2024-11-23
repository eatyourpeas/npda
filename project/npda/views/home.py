# Python imports
from asgiref.sync import sync_to_async
import datetime
import logging
from pprint import pprint


# Django imports
from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.conf import settings


# HTMX imports
from django_htmx.http import trigger_client_event

from project.npda.general_functions.csv import csv_upload, csv_parse, csv_header
from ..forms.upload import UploadFileForm
from ..general_functions.serialize_validation_errors import serialize_errors
from ..general_functions.session import (
    get_new_session_fields,
    refresh_session_object_asynchronously,
    refresh_session_object_synchronously,
)
from ..general_functions.view_preference import get_or_update_view_preference
from ..kpi_class.kpis import CalculateKPIS

# RCPCH imports
from .decorators import login_and_otp_required

# Logging
logger = logging.getLogger(__name__)


@login_and_otp_required()
async def home(request):
    """
    Home page view - contains the upload form.
    Only verified users can access this page.
    """
    if request.session.get("can_upload_csv") is False:
        # If the user does not have permission to upload csvs, redirect them to the submissions page
        return redirect("dashboard")

    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        user_csv = request.FILES["csv_upload"]
        pz_code = request.session.get("pz_code")
        if request.session.get("can_upload_csv") is True:
            # check to see if the CSV is valid - cannot accept CSVs with no header. All other header errors are non-lethal but are reported back to the user
            try:
                parsed_csv = csv_parse(user_csv)
            except ValueError as e:
                messages.error(
                    request=request,
                    message=f"Invalid CSV format: {e}",
                )
                return redirect("home")

            if (
                parsed_csv.missing_columns
                or parsed_csv.additional_columns
                or parsed_csv.duplicate_columns
            ):
                message = "Invalid CSV format."
                if parsed_csv.missing_columns:
                    message += (
                        f" Missing columns: [{", ".join(parsed_csv.missing_columns)}]"
                    )
                if parsed_csv.additional_columns:
                    message += f" Unexpected columns: [{", ".join(parsed_csv.additional_columns)}]"
                if parsed_csv.duplicate_columns:
                    message += f" Duplicate columns: [{", ".join(parsed_csv.additional_columns)}]"
                messages.error(
                    request=request,
                    message=message,
                )
                return redirect("home")

            # CSV is valid, parse any errors and store the data in the tables.
            errors_by_row_index = await csv_upload(
                user=request.user,
                dataframe=parsed_csv.df,
                csv_file=user_csv,
                pdu_pz_code=pz_code,
            )
            # log user activity
            VisitActivity = apps.get_model("npda", "VisitActivity")
            try:
                await VisitActivity.objects.acreate(
                    activity=8,
                    ip_address=request.META.get("REMOTE_ADDR"),
                    npdauser=request.user,
                )  # uploaded csv - activity 8
            except Exception as e:
                logger.error(f"Failed to log user activity: {e}")

            # update the session fields - this stores that the user has uploaded a csv and disables the ability to use the questionnaire
            await refresh_session_object_asynchronously(
                request=request, user=request.user, pz_code=pz_code
            )
            if errors_by_row_index:
                # get submission and store the errors to report back to the user in the Data Quality Report
                Submission = apps.get_model("npda", "Submission")
                submission = await Submission.objects.aget(
                    paediatric_diabetes_unit__pz_code=pz_code,
                    submission_active=True,
                    audit_year=datetime.date.today().year,
                )
                submission.errors = serialize_errors(errors_by_row_index)
                await sync_to_async(submission.save)()
                messages.error(
                    request=request,
                    message=f"CSV has been uploaded, but errors have been found in {len(errors_by_row_index.items())} rows. Please check the data quality report for details.",
                )
            else:
                messages.success(
                    request=request,
                    message="File uploaded successfully. There are no errors,",
                )
            return redirect("submissions")
        else:
            # If the user does not have permission to upload csvs, redirect them to the dashboard page
            messages.error(
                request=request,
                message=f"You have do not have permission to upload csvs for {pz_code}.",
            )
            return redirect("dashboard")

    else:
        form = UploadFileForm()

    context = {"file_uploaded": False, "form": form}
    template = "home.html"
    return render(request=request, template_name=template, context=context)


def download_template(request):
    """
    Creates the template csv for users to fill out and upload into NPDA
    """
    return HttpResponse(
        csv_header(),
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="npda_template.csv"'},
    )


def view_preference(request):
    """
    HTMX callback from the button press in the view_preference.html template.
    """

    view_preference_selection = request.POST.get("view_preference", None)
    view_preference = get_or_update_view_preference(
        request.user, view_preference_selection
    )
    pz_code = request.POST.get("pz_code_select_name", None)

    if pz_code is not None:
        new_session_fields = get_new_session_fields(
            user=request.user, pz_code=pz_code
        )  # includes a validation step
    else:
        new_session = request.session
        pz_code = new_session["pz_code"]
        new_session_fields = get_new_session_fields(
            request.user, pz_code
        )  # includes a validation step

    request.session.update(new_session_fields)
    context = {
        "view_preference": view_preference,
        "chosen_pdu": pz_code,
        "pdu_choices": request.session["pdu_choices"],
    }

    response = render(
        request, template_name="partials/view_preference.html", context=context
    )

    patients_list_view_url = reverse("patients")
    submissions_list_view_url = reverse("submissions")
    npdauser_list_view_url = reverse("npda_users")
    dashboard_url = reverse("dashboard")

    trigger_client_event(
        response=response,
        name="npda_users",
        params={"method": "GET", "url": npdauser_list_view_url},
    )  # reloads the npdauser table

    trigger_client_event(
        response=response,
        name="submissions",
        params={"method": "GET", "url": submissions_list_view_url},
    )  # reloads the submissions table

    trigger_client_event(
        response=response,
        name="patients",
        params={"method": "GET", "url": patients_list_view_url},
    )  # reloads the patients table

    trigger_client_event(
        response=response,
        name="dashboard",
        params={"method": "GET", "url": dashboard_url},
    )  # reloads the dashboard
    return response


@login_and_otp_required()
def dashboard(request):
    """
    Dashboard view for the KPIs.
    """
    template = "dashboard.html"
    pz_code = request.session.get("pz_code")
    refresh_session_object_synchronously(
        request=request, user=request.user, pz_code=pz_code
    )
    if request.htmx:
        # If the request is an htmx request, we want to return the partial template
        template = "partials/kpi_table.html"

    PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")
    try:
        pdu = PaediatricDiabetesUnit.objects.get(pz_code=pz_code)
    except PaediatricDiabetesUnit.DoesNotExist:
        messages.error(
            request=request,
            message=f"Paediatric Diabetes Unit with PZ code {pz_code} does not exist",
        )
        return render(request, "dashboard.html")

    calculate_kpis = CalculateKPIS(
        calculation_date=datetime.date.today(), return_pt_querysets=True
    )

    kpi_calculations_object = calculate_kpis.calculate_kpis_for_pdus(pz_codes=[pz_code])

    context = {
        "pdu": pdu,
        "kpi_results": kpi_calculations_object,
        "aggregation_level": "Paediatric Diabetes Unit",
    }

    return render(request, template_name=template, context=context)
