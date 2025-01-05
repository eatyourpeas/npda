import json

import plotly.graph_objects as go
import plotly.io as pio

# Django imports
from django.http import HttpResponseBadRequest
from django.shortcuts import render

from project.constants.colors import *
from project.npda.models.paediatric_diabetes_unit import (
    PaediatricDiabetesUnit as PaediatricDiabetesUnitClass,
)

import json
from datetime import date

# Django imports
from django.shortcuts import render

from project.npda.models.paediatric_diabetes_unit import (
    PaediatricDiabetesUnit as PaediatricDiabetesUnitClass,
)


from project.npda.kpi_class.kpis import CalculateKPIS


from project.npda.general_functions.map import (
    get_children_by_pdu_audit_year,
    generate_distance_from_organisation_scatterplot_figure,
    generate_dataframe_and_aggregated_distance_data_from_cases,
)
from project.npda.general_functions.rcpch_nhs_organisations import (
    fetch_organisation_by_ods_code,
)


from project.npda.views.decorators import login_and_otp_required
from project.npda.views.dashboard.dashboard import (
    KPI_CATEGORY_ATTR_MAP,
    TEXT,
    get_pt_level_table_data,
)

import logging

logger = logging.getLogger(__name__)

DEFAULT_CHART_HTML_HEIGHT = "18rem"


@login_and_otp_required()
def get_patient_level_report_partial(request):

    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    pt_level_menu_tab_selected = request.GET.get("selected")

    # State vars
    # Colour the selected menu tab
    highlight = {f"{key}": key == pt_level_menu_tab_selected for key in TEXT.keys()}

    selected_data = TEXT[pt_level_menu_tab_selected]

    # Gather the selected category's data

    # First need to get the relevant calculations
    pz_code = request.session.get("pz_code")

    selected_audit_year = int(request.session.get("selected_audit_year"))
    # TODO: remove min clamp once available audit year from preference filter sorted
    selected_audit_year = max(selected_audit_year, 2024)
    calculation_date = date(year=selected_audit_year, month=5, day=1)

    calculate_kpis = CalculateKPIS(calculation_date=calculation_date, return_pt_querysets=True)

    # Set relevant patients
    calculate_kpis.set_patients_for_calculation(pz_codes=[pz_code])

    # Run the relevant subset of calculations
    selected_kpis = KPI_CATEGORY_ATTR_MAP[pt_level_menu_tab_selected]
    kpi_calculations_object = calculate_kpis._calculate_kpis(selected_kpis)

    try:
        selected_table_headers, selected_table_data = get_pt_level_table_data(
            category=pt_level_menu_tab_selected,
            calculate_kpis_object=calculate_kpis,
            kpi_calculations_object=kpi_calculations_object,
        )
    except Exception as e:
        logger.error(
            f"Error getting pt_level_table_data for {pt_level_menu_tab_selected=} {e=}",
            exc_info=True,
        )
        # messages.error(request, f"Error getting data!")

        selected_table_headers = []
        selected_table_data = []

    return render(
        request,
        template_name="dashboard/pt_level_report_table_partial.html",
        context={
            "text": selected_data,
            "pt_level_menu_tab_selected": pt_level_menu_tab_selected,
            "highlight": highlight,
            "table_data": {
                "headers": selected_table_headers,
                "row_data": selected_table_data,
            },
        },
    )


@login_and_otp_required()
def get_waffle_chart_partial(request):
    """HTMX view that accepts a GET request with an object of waffle labels and percentages,
    returning a waffle chart rendered"""

    try:

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
            if data:
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
        Y, X = (
            GRID_SIZE - 1,
            0,
        )  # We start top left and move left to right, top to bottom

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
                        size=10,
                        color=square["colour"],
                        symbol="square",
                    ),
                    name=square["category"],
                    showlegend=False,
                    hovertemplate=f"{square['category']}<extra></extra>",
                )
            )

        # Add legend
        for idx, (label, pct) in enumerate(data):
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    marker=dict(size=10, color=colours[idx], symbol="square"),
                    name=f"{pct}% {label}",
                    # hoverinfo="skip",
                )
            )

        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(
                orientation="h",
                y=1.25,  # Move legend higher above the plot
                x=0.5,
                xanchor="center",
                font=dict(size=10),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        # Convert Plotly figure to HTML
        chart_html = fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={
                "displayModeBar": False,
            },
            default_height=DEFAULT_CHART_HTML_HEIGHT,
        )
        return render(request, "dashboard/waffle_chart_partial.html", {"chart_html": chart_html})

    except Exception as e:
        return render(
            request,
            "dashboard/waffle_chart_partial.html",
            {"error": "Something went wrong!"},
        )


@login_and_otp_required()
def get_map_chart_partial(request):

    if not request.htmx:
        return HttpResponseBadRequest("This view is only accessible via HTMX")

    # Fetch data from query parameters
    pz_code: str = request.session.get("pz_code")
    selected_audit_year = request.session.get("selected_audit_year")

    try:
        paediatric_diabetes_unit = PaediatricDiabetesUnitClass.objects.get(pz_code=pz_code)

        # get lead organisation for the selected PDU
        pdu_lead_organisation = fetch_organisation_by_ods_code(
            ods_code=paediatric_diabetes_unit.lead_organisation_ods_code
        )
    except:
        raise ValueError(
            f"Lead organisation for PDU {paediatric_diabetes_unit.lead_organisation_ods_code=} not found"
        )

    try:

        # thes are all registered patients for the current cohort at the selected organisation to be plotted in the map
        patients_to_plot = get_children_by_pdu_audit_year(
            paediatric_diabetes_unit=paediatric_diabetes_unit,
            paediatric_diabetes_unit_lead_organisation=pdu_lead_organisation,
            audit_year=selected_audit_year,
        )

        # aggregated distances (mean, median, max, min) that patients have travelled to the selected organisation
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

    except Exception as e:
        logger.error("Error generating map chart", exc_info=True)
        return render(
            request,
            "dashboard/map_chart_partial.html",
            {"error": "Something went wrong!"},
        )


@login_and_otp_required()
def get_colored_figures_chart_partial(
    request,
    colored: int,
    total_figures: int,
):
    try:

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
    except Exception as e:
        return render(
            request,
            "dashboard/colored_figures_chart_partial.html",
            {"error": "Something went wrong!"},
        )


@login_and_otp_required()
def get_simple_bar_chart_pcts_partial(request):
    """Returns a HTML simple bar chart with percentages for the given data.

    Expects:
    {
        'attr_1': {
            pct: float,
            count: int,
            total: int,
            label: str,
        },
        'attr_2': {
            ...
        }
        ...
    }

    Optionally accepts:
        request.GET.get("color"): str, hex color code to use for the bars
    """
    try:

        if not request.htmx:
            return HttpResponseBadRequest("This view is only accessible via HTMX")

        # Fetch data from query parameters

        # Bar color
        if bar_color := request.GET.get("color", None):
            # Easier just to send the hex code as a string in request url
            # so add the '#' if it's not there
            bar_color = f"#{bar_color}" if bar_color[0] != "#" else bar_color
        else:
            bar_color = RCPCH_DARK_BLUE

        # NOTE: don't need to handle empty data as the template handles this
        data_raw = json.loads(request.GET.get("data"))

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
                marker=dict(color=bar_color),
            )
        )

        # Adjust x-axis labels to avoid overlap
        if len(x) > 3:
            ticktext = []
            CUT_OFF_CHAR_LEN = 10
            for label in x:
                if len(label) > CUT_OFF_CHAR_LEN:
                    # Label too long, cut off at CUT_OFF_CHAR_LEN characters
                    ticktext.append(label[:CUT_OFF_CHAR_LEN] + "...")
                else:
                    ticktext.append(label)
        else:
            # # Wrap text with <br>
            ticktext = [label.replace(" ", "<br>") for label in x]

        # Update layout for labels and formatting
        fig.update_layout(
            title="",
            xaxis_title="",
            yaxis_title="% CYP with T1DM",
            yaxis=dict(
                range=[0, 120], # Breathing room for percentages above 100
                tickvals = [0, 25, 50, 75, 100],
                ticktext = ["0", "25", "50", "75", "100"],
            ),  
            template="simple_white",  # Clean grid style
            # Wrap text
            xaxis=dict(
                tickmode="array",
                tickvals=list(range(len(x))),
                ticktext=ticktext,
                # Rotate labels if they are too long
                tickangle=45 if len(x) > 3 else 0,
                automargin=True,  # Adjust margins for label space
            ),
            margin=dict(l=0, r=0, t=0, b=0),
        )

        chart_html = fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={
                "displayModeBar": False,
            },
            default_height=DEFAULT_CHART_HTML_HEIGHT,
        )

        return render(
            request,
            "dashboard/simple_bar_chart_pcts_partial.html",
            {"chart_html": chart_html},
        )
    except Exception as e:
        return render(
            request,
            "dashboard/simple_bar_chart_pcts_partial.html",
            {"error": "Something went wrong!"},
        )


@login_and_otp_required()
def get_hcl_scatter_plot(request):
    """HTMX view that accepts a GET request with an object of waffle labels and percentages,
    returning a waffle chart rendered.

    Must have request.GET data -> template responsible for handling empty data"""

    try:

        if not request.htmx:
            return HttpResponseBadRequest("This view is only accessible via HTMX")

        if not (request_data := request.GET.get("data", None)):
            return HttpResponseBadRequest("No data provided")

        # Fetch data from query parameters
        data = json.loads(request_data)

        # Extracting data
        quarters = [f"Q{q}" for q in data]
        percentages = [data[q]["pct"] for q in data]
        passed = [data[q]["total_passed"] for q in data]
        eligible = [data[q]["total_eligible"] for q in data]
        colors = [RCPCH_LIGHT_BLUE for _ in data]
        # highlight the last quarter
        colors[-1] = RCPCH_PINK

        # Create scatter plot
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=quarters,
                y=percentages,
                mode="lines+markers",
                marker=dict(
                    size=12,
                    color=colors,
                    symbol="square",
                ),
                line=dict(color=RCPCH_LIGHT_BLUE),
                hovertemplate="<b>%{x}</b>:Eligible passed: %{customdata[0]} / %{customdata[1]} (%{y:.1f}%)<extra></extra>",
                customdata=list(zip(passed, eligible)),
            )
        )

        # Add annotation for last quarter
        last_pct = percentages[-1]
        # Offset below point if penultimate point higher than final point
        Y_SHIFT = 20
        if len(percentages) > 1 and percentages[-2] >= last_pct:
            # If the final point is < 10, don't offset below as goes off the chart
            yshift = -Y_SHIFT if last_pct > (Y_SHIFT) else Y_SHIFT
        else:
            # Don't need to account for going off the chart at top as added space
            yshift = Y_SHIFT
        fig.add_annotation(
            x=quarters[-1],
            y=percentages[-1],
            text=f"{percentages[-1]}%",
            showarrow=False,
            font=dict(color=RCPCH_PINK, size=12),
            yshift=yshift,
        )

        # Layout adjustments
        fig.update_layout(
            xaxis=dict(title="Quarter", range=[-0.5, len(quarters) - 0.5]),
            yaxis=dict(title="% CYP with HCL Use", range=[0, 110]),
            showlegend=False,
            template="simple_white",  # Clean grid style
            margin=dict(l=0, r=0, t=0, b=0),
        )

        chart_html = fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={
                "displayModeBar": False,
            },
            default_height=DEFAULT_CHART_HTML_HEIGHT,
        )

        return render(
            request, "dashboard/hcl_scatter_plot_partial.html", {"chart_html": chart_html}
        )
    except Exception as e:
        return render(
            request,
            "dashboard/hcl_scatter_plot_partial.html",
            {"error": "Something went wrong!"},
        )
