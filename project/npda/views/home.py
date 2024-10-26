# Python imports
import datetime
import logging

# Django imports
from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.conf import settings


# HTMX imports
from django_htmx.http import trigger_client_event

from ..forms.upload import UploadFileForm
from ..general_functions.csv_summarize import csv_summarize
from ..general_functions.csv_upload import csv_upload, read_csv
from ..general_functions.session import get_new_session_fields
from ..general_functions.view_preference import get_or_update_view_preference
from ..kpi_class.kpis import CalculateKPIS

# RCPCH imports
from .decorators import login_and_otp_required

# Logging
logger = logging.getLogger(__name__)

# csv processing imports
import csv
import difflib


def error_list(wrapper_error: ValidationError):
    ret = []

    for field, errors in wrapper_error.error_dict.items():
        for error in errors:
            ret.append(
                {
                    "field": field,
                    "message": error.message,
                    "original_row_index": error.original_row_index,
                }
            )

    return ret

def get_expected_headers():
    template_path = 'static/npda_base.csv'
    with open(template_path, mode='r', newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        headers = next(reader, None)
    return headers

@login_and_otp_required()
def home(request):
    """
    Home page view - contains the upload form.
    Only verified users can access this page.
    """
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        user_csv = request.FILES["csv_upload"]
        pz_code = request.session.get("pz_code")

        # You can't read the same file twice without resetting it
        user_csv.seek(0)
        reader = csv.reader(user_csv.read().decode("utf-8").splitlines())
        user_headers = next(reader, None)

        template_headers = get_expected_headers()

        # Next localise headers so have list and say 'these are the headers affected'

        if user_headers != template_headers:
            list_diff = [header for header in user_headers if header not in template_headers]
            error_string = f'CSV headers do not match the expected format/order. Please ensure you are using the template csv provided. Headers affected, or those present in your file but not the template, are: {list_diff}. The headers uploaded must be exactly the same as the template headers, including whitespace, capital letters and ordering.'
            messages.error(request, error_string)
            return render(request, "home.html", {
                    "file_uploaded": False,
                    "form": form,
                    "errors": [error_string]
            })

        # You can't read the same file twice without resetting it
        user_csv.seek(0)
        errors = []

        try:
            csv_upload(
                user=request.user,
                dataframe=read_csv(user_csv),
                csv_file=user_csv,
                pdu_pz_code=pz_code,
            )
            messages.success(
                request=request,
                message="File uploaded successfully. There are no errors,",
            )

            VisitActivity = apps.get_model("npda", "VisitActivity")
            try:
                VisitActivity.objects.create(
                    activity=8,
                    ip_address=request.META.get("REMOTE_ADDR"),
                    npdauser=request.user,
                )  # uploaded csv - activity 8
            except Exception as e:
                logger.error(f"Failed to log user activity: {e}")
        except ValidationError as error:
            errors = error_list(error)
            for error in errors:
                messages.error(
                    request=request,
                    message=f"CSV has been uploaded, but errors have been found. These include error in row {error['original_row_index']}: {error['message']}",
                )
            pass

        return redirect("submissions")
    else:
        form = UploadFileForm()

    context = {"file_uploaded": False, "form": form}
    template = "home.html"
    return render(request=request, template_name=template, context=context)


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
