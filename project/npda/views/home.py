# Python imports
from asgiref.sync import sync_to_async
import datetime
import logging
import json
import io

from datetime import date


# Django imports
from django.apps import apps
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.conf import settings


# HTMX imports
from django_htmx.http import trigger_client_event

from project.npda.general_functions.csv import csv_upload, csv_parse, csv_header
from ..forms.upload import UploadFileForm
from ..general_functions.session import (
    get_new_session_fields,
    refresh_audit_years_in_session,
    refresh_session_object_asynchronously,
)
from ..general_functions.view_preference import get_or_update_view_preference

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
        user_csv_filename = user_csv.name
        # We are eventually storing the CSV file as a BinaryField so have to hold it in memory
        user_csv_bytes = user_csv.read()

        pz_code = request.session.get("pz_code")
        is_jersey = pz_code == "PZ248"
        if request.session.get("can_upload_csv") is True:
            # check to see if the CSV is valid - cannot accept CSVs with no header. All other header errors are non-lethal but are reported back to the user
            try:
                parsed_csv = csv_parse(io.BytesIO(user_csv_bytes), is_jersey=is_jersey)
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

            audit_year = request.session.get("selected_audit_year")

            # CSV is valid, parse any errors and store the data in the tables.
            errors_by_row_index = await csv_upload(
                user=request.user,
                dataframe=parsed_csv.df,
                csv_file_name=user_csv_filename,
                csv_file_bytes=user_csv_bytes,
                pdu_pz_code=pz_code,
                audit_year=audit_year,
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
                messages.error(
                    request=request,
                    message=f"CSV has been uploaded, but errors were found in {len(errors_by_row_index.items())} rows. Please check the data quality report for details.",
                )
            else:
                messages.success(
                    request=request,
                    message="Submission completed. There were no errors.",
                )
            return redirect("patients")
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


def download_template(request, region):
    """
    Creates the template csv for users to fill out and upload into NPDA
    """
    if region == "england_wales":
        file = csv_header()
    elif region == "jersey":
        file = csv_header(is_jersey=True)
    return HttpResponse(
        file,
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

    # Reload the page to apply the new view preference
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_and_otp_required()
def audit_year(request):
    """
    View to change the audit year for the KPIs and submissions.
    """
    if request.method == "POST":
        audit_year = request.POST.get("audit_year_select_name", None)
        refresh_audit_years_in_session(request, audit_year)

        # Reload the page to apply the new view preference
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    context = {
        "audit_years": request.session.get("audit_years"),
        "selected_audit_year": request.session.get("selected_audit_year"),
    }

    response = render(
        request, template_name="partials/audit_year_select.html", context=context
    )
