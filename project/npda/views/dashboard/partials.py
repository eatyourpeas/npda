import json

import plotly.graph_objects as go
import plotly.io as pio

# Django imports
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

import project.constants.colors as colors
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

    selected_data: dict = TEXT[pt_level_menu_tab_selected]

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
                "ineligible_hover_reason": selected_data.get("ineligible_hover_reason", {}),
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
            first_category = list(data.keys())[0]
            data[first_category] += 100 - total

        # Sort data by pct ascending so we put the smallest category top left
        data = sorted(data.items(), key=lambda item: item[1], reverse=False)

        # Prepare waffle chart
        # TODO: ADD IN A BUNCH OF COLORS HERE. ?COULD SPECIFY COLORS IN GET REQUEST
        colours = [
            colors.RCPCH_DARK_BLUE,
            colors.RCPCH_PINK,
            colors.RCPCH_MID_GREY,
            colors.RCPCH_CHARCOAL_DARK,
            colors.RCPCH_RED,
            colors.RCPCH_ORANGE,
            colors.RCPCH_YELLOW,
            colors.RCPCH_STRONG_GREEN,
            colors.RCPCH_AQUA_GREEN,
            colors.RCPCH_PURPLE,
            colors.RCPCH_PURPLE_LIGHT_TINT2,
            colors.RCPCH_PURPLE_DARK_TINT,
            colors.RCPCH_RED_LIGHT_TINT3,
            colors.RCPCH_ORANGE_LIGHT_TINT3,
            colors.RCPCH_STRONG_GREEN_LIGHT_TINT3,
            colors.RCPCH_AQUA_GREEN_LIGHT_TINT3,
            colors.RCPCH_ORANGE_LIGHT_TINT3,
            colors.RCPCH_DARK_GREY,
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
                        # Size of the square
                        size=16,
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
        logger.error("Error generating waffle chart", exc_info=True)
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
def get_progress_bar_chart_partial(
    request,
):
    """Expects request.GET to contain obj as this struct:
    {
        'attr_1': {
            "count":int,
            "total":int,
            "pct":int,
            "label":str
        },
        'attr_2": ...
    }
    """
    try:

        if not request.htmx:
            return HttpResponseBadRequest("This view is only accessible via HTMX")

        values = {}
        # Django Query dict makes vals a list so need to extact first val
        for attr, vals in request.GET.items():
            # Skip these
            if attr in [
                "kpi_8_total_deaths",
            ]:
                continue

            values[attr] = json.loads(vals)

        # Create horizontal bar chart with percentages (looking like progress bar)
        fig = go.Figure()

        # Prepare data for the chart

        labels = [values[attr]["label"] for attr in values]
        percentages = [values[attr]["pct"] for attr in values]
        counts = [f"{values[attr]['count']} / {values[attr]['total']}" for attr in values]

        # Add background bars (grey) representing 100% width
        fig.add_trace(
            go.Bar(
                x=[100] * len(values),
                y=labels,
                orientation="h",
                marker=dict(color=colors.RCPCH_LIGHT_GREY),
                showlegend=False,
                hoverinfo="none",
                name="Background",
            )
        )

        # Add text annotations above each bar
        for i, label in enumerate(labels):
            fig.add_annotation(
                x=0,  # Start of the bar
                y=i,
                text=f"{label} ({counts[i]})",
                showarrow=False,
                xanchor="left",
                yanchor="bottom",
                font=dict(size=14, color=colors.RCPCH_DARK_BLUE),
                align="left",
                yshift=27,  # Shift the text upwards for readability
            )

        # Add actual data bars (blue)
        fig.add_trace(
            go.Bar(
                x=percentages,
                y=labels,
                orientation="h",
                marker=dict(color=colors.RCPCH_DARK_BLUE),
                text=[f"{pct}%" for pct in percentages],
                textposition=["inside" if pct > 5 else "outside" for pct in percentages],
                insidetextanchor="end",
                name="Progress",
            )
        )

        # Update layout for nicer aesthet
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(
                visible=False,  # Hide x-axis
                fixedrange=True,  # Prevent zooming and scrolling on x-axis
            ),
            yaxis=dict(
                showgrid=False,  # Remove grid
                showticklabels=False,  # Hide y-axis labels
                fixedrange=True,  # Prevent zooming and scrolling on y-axis
            ),
            barmode="overlay",  # Ensure bars overlap properly
            plot_bgcolor="white",  # White background for clean visuals
            showlegend=False,  # Hide legend
            bargap=0.4,  # Increase space between bars
        )

        chart_html = fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={
                "displayModeBar": False,
                "scrollZoom": False,  # Disable scroll zoom
                "doubleClick": False,  # Disable double click zoom
                "displaylogo": False,  # Hide Plotly logo
                "modeBarButtonsToRemove": [
                    "zoom",
                    "pan",
                    "select",
                    "lasso2d",
                ],  # Remove interactive controls
            },
            # Fine tune height based on progress bars
            default_height=f"{5*len(labels)}rem",
        )

        return render(
            request,
            "dashboard/progress_bar_chart_partial.html",
            {"chart_html": chart_html},
        )
    except Exception as e:
        logger.error("Error generating colored figures chart", exc_info=True)
        return render(
            request,
            "dashboard/progress_bar_chart_partial.html",
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
            bar_color = colors.RCPCH_DARK_BLUE

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
                range=[0, 120],  # Breathing room for percentages above 100
                tickvals=[0, 25, 50, 75, 100],
                ticktext=["0", "25", "50", "75", "100"],
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
        logger.error("Error generating simple bar chart pcts", exc_info=True)
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
        all_colors = [colors.RCPCH_LIGHT_BLUE for _ in data]
        # highlight the last quarter
        all_colors[-1] = colors.RCPCH_PINK

        # Create scatter plot
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=quarters,
                y=percentages,
                mode="lines+markers",
                marker=dict(
                    size=12,
                    color=all_colors,
                    symbol="square",
                ),
                line=dict(color=colors.RCPCH_LIGHT_BLUE),
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
            font=dict(color=colors.RCPCH_PINK, size=12),
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
        logger.error("Error generating hcl scatter plot", exc_info=True)
        return render(
            request,
            "dashboard/hcl_scatter_plot_partial.html",
            {"error": "Something went wrong!"},
        )


def get_treemap_chart_partial(request):
    """
    Expects in request.GET:

    {
        # A map where keys are all parents, values are their colors (children assigned same color)
        parent_color_map : {
            "Other": colors.RCPCH_DARK_BLUE,
            ...
        },

        # Child to parent map
        child_parent_map : {
            "Not known": "Other",
            "Any other ethnic group": "Other",
            ...
        }

        # A data dict with keys being child names, values being ABSOLUTE counts in whole group
        data : {
            "Not known" : 3,
            ...
        }
    }
    """
    try:

        if not request.htmx:
            return HttpResponseBadRequest("This view is only accessible via HTMX")

        # Fetch data from query parameters
        client_errors = []
        if not (data := json.loads(request.GET.get("data"))):
            client_errors.append("No data key provided in request.GET")
        if not (parent_color_map := json.loads(request.GET.get("parent_color_map"))):
            client_errors.append("No parent_color_map key provided in request.GET")
        if not (child_parent_map := json.loads(request.GET.get("child_parent_map"))):
            client_errors.append("No child_parent_map key provided in request.GET")

        # Validate keys and vals
        for child in data:
            if child not in child_parent_map:
                client_errors.append(f"{child} not found in child_parent_map")

        parents_in_map = set(child_parent_map.values())
        for parent in parent_color_map:
            if parent not in parents_in_map:
                client_errors.append(
                    f"{parent} from parent_color_map not found in child_parent_map"
                )

        if len(client_errors) > 0:
            logger.error(f"Treemap partial bad client request with errors: {client_errors}")
            return HttpResponseBadRequest(client_errors)

        # Extract lists
        children = list(data.keys())
        percentages = list(data.values())
        parents = [child_parent_map[child] for child in children]  # Assign parents

        # Ensure unique parent labels in the treemap
        parent_labels = list(set(parents))
        # Parent values are the sum of their children
        parent_values = []
        for parent in parent_labels:
            parent_values.append(
                sum([percentages[i] for i in range(len(children)) if parents[i] == parent])
            )

        # Define all labels (parents first, then children)
        all_labels = parent_labels + children
        all_parents = ["ALL"] * len(parent_labels) + parents

        # Define values (parents first, then children)
        all_values = parent_values + percentages

        # Assign the same color to subcategories as their parent
        all_colors = {p: parent_color_map[p] for p in parent_labels}  # Assign parent colors
        all_colors.update(
            # Apply same color to children
            {child: parent_color_map[child_parent_map[child]] for child in children}
        )

        # Create Treemap
        fig = go.Figure(
            go.Treemap(
                labels=all_labels,  # Labels including parents
                parents=all_parents,  # Hierarchical structure
                values=all_values,  # Sizes
                hoverinfo="label+percent parent",  # Show labels and percentages
                marker=dict(
                    # Apply parent colors to subcategories
                    colors=[all_colors[label] for label in all_labels],
                ),
            )
        )

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
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

        return render(
            request,
            "dashboard/treemap_chart_partial.html",
            {"chart_html": chart_html},
        )

    except Exception as e:
        logger.error("Error generating treemap chart", exc_info=True)
        return render(
            request,
            "dashboard/treemap_chart_partial.html",
            {"error": "Something went wrong!"},
        )
