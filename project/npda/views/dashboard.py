# Python imports
import datetime
import logging
from datetime import date


# Django imports
from django.apps import apps
from django.contrib import messages
from django.shortcuts import render

from project.npda.general_functions.model_utils import print_instance_field_attrs


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

    print(f'{kpi_calculations_object=}\n\n{print_instance_field_attrs(pdu)=}\n')
    

    context = {
        "pdu_object": pdu,
        "kpi_calculations_object": kpi_calculations_object,
        # TODO: this should be an enum but we're currently not doing benchmarking so can update
        # at that point
        "aggregation_level": "pdu", 
    }

    return render(request, template_name=template, context=context)