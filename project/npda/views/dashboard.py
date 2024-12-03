# Python imports
import datetime
import logging
from datetime import date


# Django imports
from django.apps import apps
from django.contrib import messages
from django.shortcuts import render


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

    """
    Map of cases by distance from the selected organisation
    """

    # get submitting_cohort number - in future will be selectable
    selected_audit_year = request.session.get("selected_audit_year")

    # get lead organisation for the selected PDU
    try:
        pdu_lead_organisation = fetch_organisation_by_ods_code(
            ods_code=pdu.lead_organisation_ods_code
        )
    except:
        pdu_lead_organisation = None
        raise ValueError(f"Lead organisation for PDU {pdu.name} not found")

    # thes are all registered patients for the current cohort at the selected organisation to be plotted in the map
    patients_to_plot = get_children_by_pdu_audit_year(
        audit_year=selected_audit_year,
        paediatric_diabetes_unit=pdu,
        paediatric_diabetes_unit_lead_organisation=pdu_lead_organisation,
    )

    # aggregated distances (mean, median, max, min) that patients have travelled to the selected organisation
    aggregated_distances, patient_distances_dataframe = (
        generate_dataframe_and_aggregated_distance_data_from_cases(
            filtered_cases=patients_to_plot
        )
    )

    # generate scatterplot of patients by distance from the selected organisation
    scatterplot_of_cases_for_selected_organisation = (
        generate_distance_from_organisation_scatterplot_figure(
            geo_df=patient_distances_dataframe,
            pdu_lead_organisation=pdu_lead_organisation,
        )
    )

    context = {
        "pdu": pdu,
        "kpi_results": kpi_calculations_object,
        "aggregation_level": "Paediatric Diabetes Unit",
        "aggregated_distances": aggregated_distances,
        "scatterplot_of_cases_for_selected_organisation": scatterplot_of_cases_for_selected_organisation,
    }

    return render(request, template_name=template, context=context)