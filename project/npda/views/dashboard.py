# Python imports
from collections import defaultdict
import datetime
import json
import logging
from datetime import date

import plotly.graph_objects as go
import plotly.io as pio

# Django imports
from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.db.models import QuerySet, Count

from project.constants.colors import RCPCH_DARK_BLUE, RCPCH_MID_GREY, RCPCH_PINK
from project.constants.diabetes_types import DIABETES_TYPES
from project.npda.general_functions.model_utils import print_instance_field_attrs
from project.npda.general_functions.quarter_for_date import retrieve_quarter_for_date
from project.npda.models.paediatric_diabetes_unit import (
    PaediatricDiabetesUnit as PaediatricDiabetesUnitClass,
)


# HTMX imports
from ..general_functions.session import (
    refresh_session_object_synchronously,
)
from ..kpi_class.kpis import CalculateKPIS
from ..general_functions.map import (
    get_children_by_pdu_audit_year,
    generate_distance_from_organisation_scatterplot_figure,
    generate_dataframe_and_aggregated_distance_data_from_cases,
)
from ..general_functions.rcpch_nhs_organisations import fetch_organisation_by_ods_code

# RCPCH imports
from .decorators import login_and_otp_required

# Define our data constants
TEXT = {
    "health_checks": {
        "title": "Seven Key Care Processes",
        "description": "These care processes show the completion rate per patient for all 7 key care processes for Type 1 patients. Three of these are mandatory for patients of all ages: HbA1c, BMI, and Thyroid. The other care processes are only mandatory for patients aged 12 and above.",
    },
    "additional_care_processes": {
        "title": "Additional Care Proccesses",
        "description": "Lorem ipsum dolor sit amet consectetur adipisicing elit. Nemo veniam nihil, est adipisci quis optio esse ad neque, eligendi rem omnis earum. Adipisci at veritatis, animi sapiente corrupti commodi dolorum! ",
    },
    "care_at_diagnosis": {
        "title": "Care at Diagnosis",
        "description": "Lorem ipsum dolor sit amet consectetur adipisicing elit. Nemo veniam nihil, est adipisci quis optio esse ad neque, eligendi rem omnis earum. Adipisci at veritatis, animi sapiente corrupti commodi dolorum! ",
    },
    "outcomes": {
        "title": "Outcomes",
        "description": "Lorem ipsum dolor sit amet consectetur adipisicing elit. Nemo veniam nihil, est adipisci quis optio esse ad neque, eligendi rem omnis earum. Adipisci at veritatis, animi sapiente corrupti commodi dolorum! ",
    },
}


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

    PaediatricDiabetesUnit: PaediatricDiabetesUnitClass = apps.get_model(
        "npda", "PaediatricDiabetesUnit"
    )
    try:
        pdu = PaediatricDiabetesUnit.objects.get(pz_code=pz_code)
    except PaediatricDiabetesUnit.DoesNotExist:
        messages.error(
            request=request,
            message=f"Paediatric Diabetes Unit with PZ code {pz_code} does not exist",
        )
        return render(request, "dashboard.html")

    selected_audit_year = int(request.session.get("selected_audit_year"))
    # TODO: remove min clamp once available audit year from preference filter sorted
    selected_audit_year = max(selected_audit_year, 2024)
    calculation_date = date(year=selected_audit_year, month=5, day=1)

    calculate_kpis = CalculateKPIS(
        calculation_date=calculation_date, return_pt_querysets=True
    )

    kpi_calculations_object = calculate_kpis.calculate_kpis_for_pdus(pz_codes=[pz_code])

    # From this, gather specific chart data required

    # Total eligible patients stratified by diabetes type
    total_eligible_patients_queryset: QuerySet = kpi_calculations_object[
        "calculated_kpi_values"
    ]["kpi_1_total_eligible"]["patient_querysets"]["eligible"]
    eligible_pts_diabetes_type_counts = total_eligible_patients_queryset.values(
        "diabetes_type"
    ).annotate(count=Count("diabetes_type"))
    eligible_pts_diabetes_type_value_counts = defaultdict(int)
    for item in eligible_pts_diabetes_type_counts:
        diabetes_type = item["diabetes_type"]
        count = item["count"]

        # These are T1/T2DM types
        if diabetes_type == 1:
            diabetes_type_str = "T1DM"
            eligible_pts_diabetes_type_value_counts[diabetes_type_str] += count
        elif diabetes_type == 2:
            diabetes_type_str = "T2DM"
            eligible_pts_diabetes_type_value_counts[diabetes_type_str] += count
        else:
            # Count as 'Other rare forms'
            diabetes_type_str = "Other rare forms"
            eligible_pts_diabetes_type_value_counts[diabetes_type_str] += count

    # Convert to percentages
    eligible_pts_diabetes_type_value_counts = convert_value_counts_dict_to_pct(
        eligible_pts_diabetes_type_value_counts
    )

    # Gather other context vars
    current_date = date.today()
    days_remaining_until_audit_end_date = (
        kpi_calculations_object["audit_end_date"] - current_date
    ).days
    current_quarter = retrieve_quarter_for_date(current_date)

    # Gather defaults for htmx partials
    default_pt_level_menu_text = TEXT["health_checks"]
    default_pt_level_menu_tab_selected = "health_checks"
    highlight = {
        f"{key}": key == default_pt_level_menu_tab_selected for key in TEXT.keys()
    }

    context = {
        "pdu_object": pdu,
        # "pdu_lead_organisation": pdu_lead_organisation,
        "kpi_calculations_object": kpi_calculations_object,
        "current_date": current_date,
        "current_quarter": current_quarter,
        "days_remaining_until_audit_end_date": days_remaining_until_audit_end_date,
        "charts": {
            # Converting this to a dict for easier access in the template
            "total_eligible_patients_stratified_by_diabetes_type": {
                "data": json.dumps(eligible_pts_diabetes_type_value_counts),
                "labels": list(eligible_pts_diabetes_type_value_counts.keys()),
            },
            "map": json.dumps(
                dict(
                    pdu_pk=pdu.pk,
                    selected_audit_year=selected_audit_year,
                )
            ),
        },
        # Defaults for htmx partials
        "default_pt_level_menu_text": default_pt_level_menu_text,
        "default_pt_level_menu_tab_selected": default_pt_level_menu_tab_selected,
        "default_highlight": highlight,
        # TODO: this should be an enum but we're currently not doing benchmarking so can update
        # at that point
        "aggregation_level": "pdu",
    }

    return render(request, template_name=template, context=context)


@login_and_otp_required()
def get_patient_level_report_partial(request):

    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    pt_level_menu_tab_selected = request.GET.get("selected")

    # State vars
    # Colour the selected menu tab
    highlight = {f"{key}": key == pt_level_menu_tab_selected for key in TEXT.keys()}

    return render(
        request,
        template_name="dashboard/pt_level_report_table_partial.html",
        context={
            "text": TEXT[pt_level_menu_tab_selected],
            "pt_level_menu_tab_selected": pt_level_menu_tab_selected,
            "highlight": highlight,
        },
    )


@login_and_otp_required()
def get_waffle_chart_partial(request):
    """HTMX view that accepts a GET request with an object of waffle labels and percentages,
    returning a waffle chart rendered"""

    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    if not request.GET:
        return HttpResponseBadRequest("No data provided")

    # Fetch data from query parameters
    data = {}
    for key, value in request.GET.items():
        data[key] = int(value)

    # Ensure percentages sum to 100
    total = sum(data.values())
    if total != 100:

        first_category = list(data.keys())[0]
        data[first_category] += 100 - total

    # Sort data by pct ascending so we put the smallest category top left
    data = sorted(data.items(), key=lambda item: item[1], reverse=False)

    # Prepare waffle chart
    # TODO: ADD IN A BUNCH OF COLORS HERE. ?COULD SPECIFY COLORS IN GET REQUEST
    colours = [RCPCH_DARK_BLUE, RCPCH_PINK, RCPCH_MID_GREY][: len(data)]

    # Create Plotly waffle chart
    GRID_SIZE = 10  # 10x10 grid
    Y, X = GRID_SIZE - 1, 0  # We start top left and move left to right, top to bottom

    chart_data = []
    # For each label, add the appropriate number of squares to the chart data
    for idx, (label, num_squares) in enumerate(data):
        # For each square, append its data as current r,c, and colour
        for _ in range(num_squares):
            square_data = {
                "x": X,
                "y": Y,
                "colour": colours[idx],
                "category": label,
            }
            chart_data.append(square_data)

            # Move our position

            # Move X to the right
            X += 1

            # If we've gone beyond the end of the row, set X to 0 and move Y down
            if X == GRID_SIZE:
                X = 0
                Y -= 1

    fig = go.Figure()
    for square in chart_data:

        fig.add_trace(
            go.Scatter(
                x=[square["x"]],
                y=[square["y"]],
                mode="markers",
                marker=dict(size=20, color=square["colour"], symbol="square"),
                name=square["category"],
                showlegend=False,
            )
        )

    # Add legend
    for idx, (label, pct) in enumerate(data):
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=15, color=colours[idx], symbol="square"),
                name=f"{pct}% {label}",
            )
        )

    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    # Convert Plotly figure to HTML
    chart_html = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": False},
    )
    return render(
        request, "dashboard/waffle_chart_partial.html", {"chart_html": chart_html}
    )


@login_and_otp_required()
def get_map_chart_partial(request):

    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    # Fetch data from query parameters
    pz_code: str = request.session.get("pz_code")
    selected_audit_year = request.session.get("selected_audit_year")

    paediatric_diabetes_unit = PaediatricDiabetesUnitClass.objects.get(pz_code=pz_code)

    # # get lead organisation for the selected PDU
    try:
        pdu_lead_organisation = fetch_organisation_by_ods_code(
            ods_code=paediatric_diabetes_unit.lead_organisation_ods_code
        )
    except:
        raise ValueError(
            f"Lead organisation for PDU {paediatric_diabetes_unit.lead_organisation_ods_code=} not found"
        )

    # # thes are all registered patients for the current cohort at the selected organisation to be plotted in the map
    patients_to_plot = get_children_by_pdu_audit_year(
        paediatric_diabetes_unit=paediatric_diabetes_unit,
        paediatric_diabetes_unit_lead_organisation=pdu_lead_organisation,
        audit_year=selected_audit_year,
    )

    # # aggregated distances (mean, median, max, min) that patients have travelled to the selected organisation
    aggregated_distances, patient_distances_dataframe = (
        generate_dataframe_and_aggregated_distance_data_from_cases(
            filtered_cases=patients_to_plot
        )
    )

    # generate scatterplot of patients by distance from the selected organisation
    scatterplot_of_cases_for_selected_organisation_fig = (
        generate_distance_from_organisation_scatterplot_figure(
            geo_df=patient_distances_dataframe,
            pdu_lead_organisation=pdu_lead_organisation,
            paediatric_diabetes_unit=paediatric_diabetes_unit,
        )
    )

    return render(
        request,
        template_name="dashboard/map_chart_partial.html",
        context={
            "chart_html": pio.to_html(
                scatterplot_of_cases_for_selected_organisation_fig,
                full_html=False,
                include_plotlyjs=False,
                config={"displayModeBar": True},
            ),
            "aggregated_distances": aggregated_distances,
        },
    )


def convert_value_counts_dict_to_pct(value_counts_dict: dict):
    """
    Convert a value counts dict to percentages
    """
    total = sum(value_counts_dict.values())

    value_counts_dict_pct = {}

    for key, value in value_counts_dict.items():
        value_counts_dict_pct[key] = int(value / total * 100)

    return value_counts_dict_pct
