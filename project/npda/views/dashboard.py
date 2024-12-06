# Python imports
from collections import defaultdict
import datetime
import logging
from datetime import date

import plotly.graph_objects as go

# Django imports
from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.db.models import QuerySet, Count

from project.constants.colors import RCPCH_DARK_BLUE, RCPCH_MID_GREY, RCPCH_PINK
from project.constants.diabetes_types import DIABETES_TYPES
from project.npda.general_functions.model_utils import print_instance_field_attrs
from project.npda.general_functions.quarter_for_date import retrieve_quarter_for_date


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

    PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")
    try:
        pdu = PaediatricDiabetesUnit.objects.get(pz_code=pz_code)
    except PaediatricDiabetesUnit.DoesNotExist:
        messages.error(
            request=request,
            message=f"Paediatric Diabetes Unit with PZ code {pz_code} does not exist",
        )
        return render(request, "dashboard.html")

    calculate_kpis = CalculateKPIS(calculation_date=datetime.date.today(), return_pt_querysets=True)

    kpi_calculations_object = calculate_kpis.calculate_kpis_for_pdus(pz_codes=[pz_code])

    # From this, gather specific chart data required

    # Total eligible patients stratified by diabetes type
    total_eligible_patients_queryset: QuerySet = kpi_calculations_object["calculated_kpi_values"][
        "kpi_1_total_eligible"
    ]["patient_querysets"]["eligible"]
    eligible_pts_diabetes_type_counts = total_eligible_patients_queryset.values(
        "diabetes_type"
    ).annotate(count=Count("diabetes_type"))
    diabetes_type_map = dict(DIABETES_TYPES)
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
    # Prep for chart
    total_eligible_patients_stratified_by_diabetes_type_html = (
        generate_total_eligible_patients_stratified_by_diabetes_type_html(
            data=eligible_pts_diabetes_type_value_counts
        )
    )
    
    # TODO: @eatyourpeas pls help fix
    # # Map of cases by distance from the selected organisation

    # # get submitting_cohort number - in future will be selectable
    # selected_audit_year = request.session.get("selected_audit_year")

    # # get lead organisation for the selected PDU
    # try:
    #     pdu_lead_organisation = fetch_organisation_by_ods_code(
    #         ods_code=pdu.lead_organisation_ods_code
    #     )
    # except:
    #     pdu_lead_organisation = None
    #     raise ValueError(f"Lead organisation for PDU {pdu.name} not found")

    # # thes are all registered patients for the current cohort at the selected organisation to be plotted in the map
    # patients_to_plot = get_children_by_pdu_audit_year(
    #     audit_year=selected_audit_year,
    #     paediatric_diabetes_unit=pdu,
    #     paediatric_diabetes_unit_lead_organisation=pdu_lead_organisation,
    # )

    # # aggregated distances (mean, median, max, min) that patients have travelled to the selected organisation
    # aggregated_distances, patient_distances_dataframe = (
    #     generate_dataframe_and_aggregated_distance_data_from_cases(
    #         filtered_cases=patients_to_plot
    #     )
    # )

    # # generate scatterplot of patients by distance from the selected organisation
    # scatterplot_of_cases_for_selected_organisation = (
    #     generate_distance_from_organisation_scatterplot_figure(
    #         geo_df=patient_distances_dataframe,
    #         pdu_lead_organisation=pdu_lead_organisation,
    #     )
    # )

    

    print(f"{kpi_calculations_object=}\n")
    print_instance_field_attrs(pdu)

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
        "kpi_calculations_object": kpi_calculations_object,
        "current_date": current_date,
        "current_quarter": current_quarter,
        "days_remaining_until_audit_end_date": days_remaining_until_audit_end_date,
        "charts": {
            "total_eligible_patients_stratified_by_diabetes_type": total_eligible_patients_stratified_by_diabetes_type_html,
            # "scatterplot_of_cases_for_selected_organisation": scatterplot_of_cases_for_selected_organisation,
            # "aggregated_distances": aggregated_distances,
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


def generate_total_eligible_patients_stratified_by_diabetes_type_html(data: dict) -> str:
    """
    Generates the HTML for the total eligible patients stratified by diabetes type.

    Returns the HTML string.
    """

    # Define the colours for each category
    colours = [RCPCH_DARK_BLUE, RCPCH_MID_GREY, RCPCH_PINK]

    # Total patients
    total = sum(data.values())

    # Calculate the proportion for each category
    proportions = [value / total for value in data.values()]

    # Create a grid for the waffle chart (10x10)
    grid_size = 10
    total_squares = grid_size * grid_size

    # Calculate the number of squares for each category
    squares = [round(p * total_squares) for p in proportions]

    # Create the waffle chart layout
    waffle_grid = []
    for category, count, colour in zip(data.keys(), squares, colours):
        waffle_grid.extend([colour] * count)

    # Fill the remaining squares if there's rounding discrepancy
    waffle_grid.extend(["#FFFFFF"] * (total_squares - len(waffle_grid)))

    # Convert the grid into a 10x10 matrix
    grid_matrix = [waffle_grid[i : i + grid_size] for i in range(0, total_squares, grid_size)]

    # Create the figure
    fig = go.Figure()

    # Add rectangles for the grid with gaps
    for row_index, row in enumerate(grid_matrix):
        for col_index, colour in enumerate(row):
            fig.add_trace(
                go.Scatter(
                    x=[col_index * 1.2],  # Add gaps by scaling positions
                    y=[-row_index * 1.2],  # Negative index for reverse order
                    mode="markers",
                    marker=dict(
                        size=18,  # Square size
                        color=(
                            colour if colour != "#FFFFFF" else "rgba(0,0,0,0)"
                        ),  # Transparent for empty squares
                        symbol="square",
                        line=dict(width=1, color="rgba(0,0,0,0.2)"),  # Add borders for clarity
                    ),
                    showlegend=False,
                )
            )

    # Add legend with percentages
    for category, colour, proportion in zip(data.keys(), colours, proportions):
        fig.add_trace(
            go.Scatter(
                x=[None],  # Dummy data for legend
                y=[None],
                mode="markers+text",
                marker=dict(
                    size=15,  # Legend marker size
                    color=colour,
                    symbol="square",
                ),
                text=f"{round(proportion * 100)}% {category}",
                textposition="middle right",
                textfont=dict(size=12),
                showlegend=True,
            )
        )

    # Update layout for no background
    fig.update_layout(
        title_text="Total Eligible Patients",
        title_font=dict(size=18, family="Arial", color=RCPCH_DARK_BLUE),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        margin=dict(l=10, r=10, t=50, b=10),  # Compact margins
        height=300,
        width=300,
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent paper
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
    )

    # Generate the Plotly HTML
    chart_html = fig.to_html(full_html=False)

    return chart_html
