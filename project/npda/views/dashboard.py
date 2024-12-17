# Python imports
from collections import Counter, defaultdict
import datetime
import json
import logging
from pprint import pprint
from datetime import date
from typing import Literal

import plotly.graph_objects as go

# Django imports
from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.db.models import QuerySet, Count

from project.constants.colors import *
from project.constants.diabetes_types import DIABETES_TYPES
from project.constants.ethnicities import ETHNICITIES
from project.constants.sex_types import SEX_TYPE
from project.constants.types.kpi_types import KPIRegistry
from project.npda.general_functions.model_utils import print_instance_field_attrs
from project.npda.general_functions.quarter_for_date import retrieve_quarter_for_date
from project.npda.models.paediatric_diabetes_unit import (
    PaediatricDiabetesUnit as PaediatricDiabetesUnitClass,
)
from project.npda.models.patient import Patient


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
    refresh_session_object_synchronously(request=request, user=request.user, pz_code=pz_code)

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

    calculate_kpis = CalculateKPIS(calculation_date=calculation_date, return_pt_querysets=True)

    kpi_calculations_object = calculate_kpis.calculate_kpis_for_pdus(pz_codes=[pz_code])

    # From this, gather specific chart data required

    # Total eligible patients stratified by diabetes type
    total_eligible_pts_diabetes_type_value_counts = (
        get_total_eligible_pts_diabetes_type_value_counts(
            eligible_pts_queryset=kpi_calculations_object["calculated_kpi_values"][
                "kpi_1_total_eligible"
            ]["patient_querysets"]["eligible"]
        )
    )

    # Patient characteristics -> KPI [4, 5, 6, 8, 9, 10, 11, 12]
    pt_characteristics_value_counts = get_pt_characteristics_value_counts_pct(
        calculate_kpis.kpi_name_registry,
        kpi_calculations_object["calculated_kpi_values"],
    )
    # A single chart has 5 figures -> based on pct, return the number of figures coloured
    pt_characteristics_value_counts_with_figure_counts = add_number_of_figures_coloured_for_chart(
        pt_characteristics_value_counts
    )

    # Care at diagnosis - kpis 41-43
    # Get attr names for KPIs 41, 42, 43
    kpi_41_attr_name = calculate_kpis.kpi_name_registry.get_attribute_name(41)
    kpi_42_attr_name = calculate_kpis.kpi_name_registry.get_attribute_name(42)
    kpi_43_attr_name = calculate_kpis.kpi_name_registry.get_attribute_name(43)
    care_at_diagnosis_value_counts_pct = get_care_at_diagnosis_vcs_pct(
        kpi_41_values=kpi_calculations_object["calculated_kpi_values"][kpi_41_attr_name],
        kpi_42_values=kpi_calculations_object["calculated_kpi_values"][kpi_42_attr_name],
        kpi_43_values=kpi_calculations_object["calculated_kpi_values"][kpi_43_attr_name],
    )
    pprint(f"{care_at_diagnosis_value_counts_pct=}")

    # Health checks
    # Get attr names for KPIs 32.1, 32.2, 32.3
    kpi_32_1_attr_name = calculate_kpis.kpi_name_registry.get_attribute_name(321)
    kpi_32_2_attr_name = calculate_kpis.kpi_name_registry.get_attribute_name(322)
    kpi_32_3_attr_name = calculate_kpis.kpi_name_registry.get_attribute_name(323)
    hc_completion_rate_value_counts_pct = get_hc_completion_rate_vcs(
        kpi_32_1_values=kpi_calculations_object["calculated_kpi_values"][kpi_32_1_attr_name],
        kpi_32_2_values=kpi_calculations_object["calculated_kpi_values"][kpi_32_2_attr_name],
        kpi_32_3_values=kpi_calculations_object["calculated_kpi_values"][kpi_32_3_attr_name],
    )

    # Sex, Ethnicity, IMD
    pt_sex_value_counts, pt_ethnicity_value_counts, pt_imd_value_counts = (
        get_pt_demographic_value_counts(
            all_eligible_pts_queryset=kpi_calculations_object["calculated_kpi_values"][
                "kpi_1_total_eligible"
            ]["patient_querysets"]["eligible"]
        )
    )
    # Convert to pcts
    pt_sex_value_counts_pct = convert_value_counts_dict_to_pct(pt_sex_value_counts)
    pt_ethnicity_value_counts_pct = convert_value_counts_dict_to_pct(pt_ethnicity_value_counts)
    pt_imd_value_counts_pct = convert_value_counts_dict_to_pct(pt_imd_value_counts)

    # Gather other context vars
    current_date = date.today()
    days_remaining_until_audit_end_date = (
        kpi_calculations_object["audit_end_date"] - current_date
    ).days
    current_quarter = retrieve_quarter_for_date(current_date)

    # Gather defaults for htmx partials
    default_pt_level_menu_text = TEXT["health_checks"]
    default_pt_level_menu_tab_selected = "health_checks"
    highlight = {f"{key}": key == default_pt_level_menu_tab_selected for key in TEXT.keys()}

    context = {
        "pdu_object": pdu,
        # "pdu_lead_organisation": pdu_lead_organisation,
        "kpi_calculations_object": kpi_calculations_object,
        "current_date": current_date,
        "current_quarter": current_quarter,
        "days_remaining_until_audit_end_date": days_remaining_until_audit_end_date,
        "charts": {
            "total_eligible_patients_stratified_by_diabetes_type": {
                "data": json.dumps(total_eligible_pts_diabetes_type_value_counts),
                "labels": list(total_eligible_pts_diabetes_type_value_counts.keys()),
            },
            "pt_characteristics_value_counts": {
                "data": pt_characteristics_value_counts_with_figure_counts,
            },
            "care_at_diagnosis_value_count": {
                "data": json.dumps(care_at_diagnosis_value_counts_pct),
            },
            "hc_completion_rate_value_counts_pct": {
                "data": json.dumps(hc_completion_rate_value_counts_pct),
            },
            "pt_sex_value_counts_pct": {
                "data": json.dumps(pt_sex_value_counts_pct),
            },
            "pt_ethnicity_value_counts_pct": {
                "data": json.dumps(pt_ethnicity_value_counts_pct),
            },
            "pt_imd_value_counts_pct": {
                "data": json.dumps(pt_imd_value_counts_pct),
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

    # Fetch data from query parameters
    data = {}
    for key, value in request.GET.items():
        data[key] = int(value)

    # Handle empty data (eg. if no eligible pts)
    if not data:
        return render(request, "dashboard/waffle_chart_partial.html", {"chart_html": None})

    # Ensure percentages sum to 100
    total = sum(data.values())
    if total != 100:

        first_category = list(data.keys())[0]
        data[first_category] += 100 - total

    # Sort data by pct ascending so we put the smallest category top left
    data = sorted(data.items(), key=lambda item: item[1], reverse=False)

    # Prepare waffle chart
    # TODO: ADD IN A BUNCH OF COLORS HERE. ?COULD SPECIFY COLORS IN GET REQUEST
    colours = [
        RCPCH_DARK_BLUE,
        RCPCH_PINK,
        RCPCH_MID_GREY,
        RCPCH_CHARCOAL_DARK,
        RCPCH_RED,
        RCPCH_ORANGE,
        RCPCH_YELLOW,
        RCPCH_STRONG_GREEN,
        RCPCH_AQUA_GREEN,
        RCPCH_PURPLE,
        RCPCH_PURPLE_LIGHT_TINT2,
        RCPCH_PURPLE_DARK_TINT,
        RCPCH_RED_LIGHT_TINT3,
        RCPCH_ORANGE_LIGHT_TINT3,
        RCPCH_STRONG_GREEN_LIGHT_TINT3,
        RCPCH_AQUA_GREEN_LIGHT_TINT3,
        RCPCH_ORANGE_LIGHT_TINT3,
        RCPCH_DARK_GREY,
    ][: len(data)]

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
                marker=dict(
                    size=25,
                    color=square["colour"],
                    symbol="square",
                ),
                name=square["category"],
                showlegend=False,
                hoverinfo="skip",
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
                hoverinfo="skip",
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
        config={
            "displayModeBar": False,
            "staticPlot": True,
        },
    )
    return render(request, "dashboard/waffle_chart_partial.html", {"chart_html": chart_html})


@login_and_otp_required()
def get_map_chart_partial(request):

    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    # Fetch data from query parameters
    pdu_pk: str = request.GET.get("pdu_pk")
    selected_audit_year = int(request.GET.get("selected_audit_year"))

    pdu = PaediatricDiabetesUnitClass.objects.get(pk=pdu_pk)

    # # Map of cases by distance from the selected organisation

    # # get lead organisation for the selected PDU
    try:
        pdu_lead_organisation = fetch_organisation_by_ods_code(
            ods_code=pdu.lead_organisation_ods_code
        )
    except:
        raise ValueError(f"Lead organisation for PDU {pdu.lead_organisation_ods_code=} not found")

    # # thes are all registered patients for the current cohort at the selected organisation to be plotted in the map
    patients_to_plot = get_children_by_pdu_audit_year(
        paediatric_diabetes_unit=pdu,
        paediatric_diabetes_unit_lead_organisation=pdu_lead_organisation,
        audit_year=selected_audit_year,
    )

    # # aggregated distances (mean, median, max, min) that patients have travelled to the selected organisation
    aggregated_distances, patient_distances_dataframe = (
        generate_dataframe_and_aggregated_distance_data_from_cases(filtered_cases=patients_to_plot)
    )

    # generate scatterplot of patients by distance from the selected organisation
    scatterplot_of_cases_for_selected_organisation_fig = (
        generate_distance_from_organisation_scatterplot_figure(
            geo_df=patient_distances_dataframe,
            pdu_lead_organisation=pdu_lead_organisation,
        )
    )

    chart_html = scatterplot_of_cases_for_selected_organisation_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": False},
    )

    return render(
        request,
        template_name="dashboard/map_chart_partial.html",
        context={
            "chart_html": chart_html,
        },
    )


@login_and_otp_required()
def get_colored_figures_chart_partial(
    request,
    colored: int,
    total_figures: int,
):

    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    # Get a list of booleans to determine which figures are colored (to iterate easily in the
    # template)
    is_colored = [True if i < colored else False for i in range(total_figures)]

    return render(
        request,
        "dashboard/colored_figures_chart_partial.html",
        context={
            "is_colored": is_colored,
        },
    )


@login_and_otp_required()
def get_simple_bar_chart_pcts_partial(request):
    """Returns a HTML simple bar chart with percentages for the given data.

    Expects:
    {
        'attr_1': {
            pct: int,
            total_passed: int,
            total_eligible: int,
            label: str,
        },
        'attr_2': {
            ...
        }
        ...
    }
    """
    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    # Fetch data from query parameters
    # NOTE: don't need to handle empty data as the template handles this
    data_raw = json.loads(request.GET.get("data"))
    print(f"{data_raw=}")

    x, y = [], []
    for _, values in data_raw.items():
        x.append(values["label"])
        y.append(values["pct"])

    # Create the bar chart
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=x,
            y=y,
            text=y,
            textposition="outside",
            marker=dict(color=RCPCH_LIGHT_BLUE),
        )
    )

    # Update layout for labels and formatting
    fig.update_layout(
        title="",
        xaxis_title="",
        yaxis_title="% CYP with T1DM",
        yaxis=dict(range=[0, 100]),  # Fix range from 0 to 100
        template="simple_white",  # Clean grid style
        # Wrap text
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(x))),
            ticktext=[label.replace(" ", "<br>") for label in x],  # Wrap text with <br>
            tickangle=0,  # Ensure text is horizontal
            automargin=True,  # Adjust margins for label space
        ),
    )

    chart_html = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={
            "displayModeBar": False,
        },
    )

    return render(
        request,
        "dashboard/simple_bar_chart_pcts_partial.html",
        {"chart_html": chart_html},
    )


def get_total_eligible_pts_diabetes_type_value_counts(eligible_pts_queryset: QuerySet) -> dict:
    """Gets value counts dict for total eligible patients stratified by diabetes type

    Returns empty dict if no eligible pts."""

    eligible_pts_diabetes_type_counts = eligible_pts_queryset.values("diabetes_type").annotate(
        count=Count("diabetes_type")
    )

    if not eligible_pts_diabetes_type_counts.exists():
        return {}

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

    return eligible_pts_diabetes_type_value_counts


def get_pt_characteristics_value_counts_pct(
    kpi_name_registry: KPIRegistry,
    kpi_calculations_object: dict,
) -> dict[
    Literal["care", "died_or_transitioned", "comorbidity_and_testing"],
    dict[Literal["total_eligible", "total_ineligible", "pct"], int],
]:
    """Gets value counts dict for:

    care
    - age_gte_12yo (KPI4)
    - complete_year_of_care (KPI5)
    - age_gte_12yo_and_complete_year_of_care (KPI6)

    died_or_transitioned
    - died (KPI8)
    - transitioned (KPI9)

    comorbidity_and_testing
    - coeliac (KPI10)
    - thyroid (kpi11)
    - ketone_testing (KPI12)

    NOTE: rounds DOWN (convert float to int) for percentage calculation
    """
    # Get attribute names and labels
    relevant_kpis = [4, 5, 6, 8, 9, 10, 11, 12]
    kpi_attr_names = [kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis]

    value_counts = defaultdict(lambda: {"count": 0, "total": 0, "pct": 0})
    # These are all just counts so only total_eligble and total_ineligible have values
    for kpi_attr in kpi_attr_names:

        total_eligible = kpi_calculations_object[kpi_attr]["total_eligible"]
        total_ineligible = kpi_calculations_object[kpi_attr]["total_ineligible"]

        # Need all 3 for front end chart
        value_counts[kpi_attr]["count"] = total_eligible
        value_counts[kpi_attr]["total"] = total_eligible + total_ineligible
        value_counts[kpi_attr]["pct"] = (
            int(total_eligible / value_counts[kpi_attr]["total"] * 100)
            if value_counts[kpi_attr]["total"] > 0
            else 0
        )

    # Now put into the 3 categories
    categories_vc = defaultdict(dict)
    for kpi in [4, 5, 6]:
        kpi_attr = kpi_name_registry.get_attribute_name(kpi)
        categories_vc["care"][kpi_attr] = value_counts[kpi_attr]

    for kpi in [8, 9]:
        kpi_attr = kpi_name_registry.get_attribute_name(kpi)
        categories_vc["died_or_transitioned"][kpi_attr] = value_counts[kpi_attr]

    for kpi in [10, 11, 12]:
        kpi_attr = kpi_name_registry.get_attribute_name(kpi)
        categories_vc["comorbidity_and_testing"][kpi_attr] = value_counts[kpi_attr]

    return dict(categories_vc)


def get_care_at_diagnosis_vcs_pct(
    kpi_41_values: dict,
    kpi_42_values: dict,
    kpi_43_values: dict,
) -> dict:
    """Get value counts for care at diagnosis KPIs (41, 42, 43)

    - coeliac (KPI41)
    - thyroid (KPI42)
    - carb counting ed (KPI43)

    NOTE: rounds DOWN (convert float to int) for percentage calculation
    """
    data = {}

    data["coeliac_disease_screening"] = {
        "total_passed": kpi_41_values["total_passed"],
        "total_eligible": kpi_41_values["total_eligible"],
        "pct": (
            int(kpi_41_values["total_passed"] / kpi_41_values["total_eligible"] * 100)
            if kpi_41_values["total_eligible"]
            else 0
        ),
        "label": "Coeliac Disease Screening",
    }

    data["thyroid_disease_screening"] = {
        "total_passed": kpi_42_values["total_passed"],
        "total_eligible": kpi_42_values["total_eligible"],
        "pct": (
            int(kpi_42_values["total_passed"] / kpi_42_values["total_eligible"] * 100)
            if kpi_42_values["total_eligible"]
            else 0
        ),
        "label": "Thyroid Disease Screening",
    }

    data["carbohydrate_counting_education"] = {
        "total_passed": kpi_43_values["total_passed"],
        "total_eligible": kpi_43_values["total_eligible"],
        "pct": (
            int(kpi_43_values["total_passed"] / kpi_43_values["total_eligible"] * 100)
            if kpi_43_values["total_eligible"]
            else 0
        ),
        "label": "Carbohydrate Counting Education",
    }

    return data


def get_pt_demographic_value_counts(
    all_eligible_pts_queryset: QuerySet[Patient],
) -> tuple[
    dict[Literal["Female", "Male", "Unknown"], int],
    dict[str, int],
    dict[
        Literal[
            1,
            2,
            3,
            4,
            5,
        ],
        int,
    ],
]:
    """Get value counts for pt demographics:

    - sex
    - ethnicity
    - imd
    """

    all_values = all_eligible_pts_queryset.values(
        "sex", "ethnicity", "index_of_multiple_deprivation_quintile"
    )
    sex_map = dict(SEX_TYPE)
    sex_counts = Counter(sex_map[item["sex"]] for item in all_values)
    ethnicity_map = dict(ETHNICITIES)
    ethnicity_counts = Counter(ethnicity_map[item["ethnicity"]] for item in all_values)
    imd_map = {
        1: "1st Quintile",
        2: "2nd Quintile",
        3: "3rd Quintile",
        4: "4th Quintile",
        5: "5th Quintile",
    }
    imd_counts = Counter(
        imd_map[item["index_of_multiple_deprivation_quintile"]] for item in all_values
    )

    return (
        sex_counts,
        ethnicity_counts,
        imd_counts,
    )


def get_hc_completion_rate_vcs(
    kpi_32_1_values: dict,
    kpi_32_2_values: dict,
    kpi_32_3_values: dict,
):
    """
    Get value counts for health checks completion rates
    """

    # Just need pass and fail
    vcs = {}
    for ix, kpi_values in enumerate([kpi_32_1_values, kpi_32_2_values, kpi_32_3_values], start=1):
        if ix == 1:
            kpi_label = "< 12 years old"
        elif ix == 2:
            kpi_label = ">= 12 years old"
        else:
            kpi_label = "Overall"

        vcs[f"kpi_32_{ix}_values"] = {
            "total_passed": kpi_values["total_passed"],
            "total_eligible": kpi_values["total_eligible"],
            "pct": (
                int(kpi_values["total_passed"] / kpi_values["total_eligible"] * 100)
                if kpi_values["total_passed"]
                else 0
            ),
            "label": kpi_label,
        }

    return vcs


def add_number_of_figures_coloured_for_chart(
    value_counts_dict: dict[
        Literal["care", "died_or_transitioned", "comorbidity_and_testing"],
        dict[Literal["total_eligible", "total_ineligible", "pct"], int],
    ],
    n_figures_total: int = 5,
) -> dict[Literal["total_eligible", "total_ineligible", "pct", "figures_coloured"], int]:
    """
    Add number of figures coloured to a value counts dict
    """
    # divisor is 100 / n_figures_total
    divisor = 100 / n_figures_total

    for category, vcs in value_counts_dict.items():
        for key, value in vcs.items():
            value_counts_dict[category][key]["figures_coloured"] = int(value["pct"] / divisor)

    return dict(value_counts_dict)


def convert_value_counts_dict_to_pct(value_counts_dict: dict):
    """
    Convert a value counts dict to percentages
    """
    total = sum(value_counts_dict.values())

    value_counts_dict_pct = {}

    for key, value in value_counts_dict.items():
        value_counts_dict_pct[key] = int(value / total * 100)

    return value_counts_dict_pct
