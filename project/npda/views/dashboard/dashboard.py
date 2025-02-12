# Python imports
import json
import logging
from dateutil.relativedelta import relativedelta
from datetime import date


from django.apps import apps
from django.contrib import messages
from django.shortcuts import render

from project import constants
from project.npda.general_functions.quarter_for_date import retrieve_quarter_for_date
from project.npda.models.paediatric_diabetes_unit import (
    PaediatricDiabetesUnit as PaediatricDiabetesUnitClass,
)
from project.npda.models.patient import Patient
from .helpers import *


from project.npda.general_functions.session import (
    refresh_session_object_synchronously,
)
from project.npda.kpi_class.kpis import CalculateKPIS

from project.npda.views.decorators import login_and_otp_required
from project.npda.views.dashboard.template_data import *


# LOGGING
logger = logging.getLogger(__name__)


# 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
# 🚨 TODO SHOULD BE REMOVED, JUST DURING DEV  🚨
# 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
@login_and_otp_required()
def temp_set_eligible_kpi_7(request):
    """Temporary util to set some seeded patients attrs manually

    KPI7
        to be eligible for kpi 7 (T1DM diagnosed
        during the audit period) which is denominator for kpis 41-43.

        This is because the default behaviour of the `PatientFactory` .build method (used in the
        csv seeder) is to choose a random diabetes_diagnosis between the pt's DoB and audit_start_date.

    """
    if not request.user.is_superuser:
        logger.error("User %s tried to run temp util to set KPI 7", request.user)
        raise PermissionError("Only superusers can run this util")

    from django.http import HttpResponse

    _ = 10
    logger.error(f"🔥 Setting {_} patients to be eligible for KPI 7")
    to_set_kpi_7_eligible = Patient.objects.filter(
        diabetes_type=constants.diabetes_types.DIABETES_TYPES[0][0]
    )[:_]
    for pt in to_set_kpi_7_eligible:
        pt.diagnosis_date = CalculateKPIS().audit_start_date + relativedelta(months=4)
        pt.save()
        logger.warning(f"Succesfully set {pt} to be eligible for KPI 7")

    return HttpResponse(
        f"Set {_} patients to be eligible for KPI 7: {''.join([f'<p>{pt.nhs_number}</p>' for pt in to_set_kpi_7_eligible])}",
        status=200,
    )


# 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
# 🚨 TODO SHOULD BE REMOVED, JUST DURING DEV  🚨
# 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨


@login_and_otp_required()
def dashboard(request):
    """
    Dashboard view for the KPIs.
    """
    template = "dashboard.html"
    if request.htmx:
        template = "dashboard/dashboard_base.html"
    pz_code = request.session.get("pz_code")
    refresh_session_object_synchronously(request=request)

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

    if selected_audit_year <= 2024:
        # The day after the audit year end date
        calculation_date = date(selected_audit_year, 4, 1)
    else:
        today = date.today()
        calculation_date = date(selected_audit_year, today.month, today.day)

    calculate_kpis = CalculateKPIS(calculation_date=calculation_date, return_pt_querysets=True)

    kpi_calculations_object = calculate_kpis.calculate_kpis_for_pdus(pz_codes=[pz_code])
    # Extract helpers
    get_attribute_name = calculate_kpis.kpi_name_registry.get_attribute_name

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
    # Add labels for frontend
    pt_char_attr_labels_map = {
        get_attribute_name(4): "Aged 12+",
        get_attribute_name(5): "Complete year of care",
        get_attribute_name(6): "Aged 12+ with complete year of care",
        get_attribute_name(8): "Died",
        get_attribute_name(9): "Transitioned",
        get_attribute_name(10): "Coeliac disease",
        get_attribute_name(11): "Thyroid disease",
        get_attribute_name(12): "Ketone testing",
    }
    for attr_name in pt_char_attr_labels_map:
        for category in ["care", "died_or_transitioned", "comorbidity_and_testing"]:
            if attr_name in pt_characteristics_value_counts[category]:
                pt_characteristics_value_counts[category][attr_name]["label"] = (
                    pt_char_attr_labels_map[attr_name]
                )

    # Get TreatmentRegimen / Glucose Monitoring
    tx_regimen_value_counts_pct = get_tx_regimen_value_counts_pcts(
        calculate_kpis.kpi_name_registry,
        kpi_calculations_object["calculated_kpi_values"],
    )
    glucose_monitoring_value_counts_pct = get_glucose_monitoring_value_counts_pcts(
        calculate_kpis.kpi_name_registry,
        kpi_calculations_object["calculated_kpi_values"],
    )

    # HCL Use
    hcl_use_per_quarter_value_counts_pct = calculate_kpis.get_kpi_24_hcl_use_stratified_by_quarter()

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

    # Additional care processes
    # Get attr names for KPIs 33-40
    additional_care_processes_kpi_attr_names = [
        calculate_kpis.kpi_name_registry.get_attribute_name(kpi) for kpi in range(33, 41)
    ]
    additional_care_processes_value_counts_pct = get_additional_care_processes_value_counts(
        additional_care_processes_kpi_attr_names=additional_care_processes_kpi_attr_names,
        kpi_calculations_object=kpi_calculations_object["calculated_kpi_values"],
    )

    # Outcomes
    # HbA1c 44+45 (mean, median)
    # Annoyingly have to do this sync inside view as need the calculate_kpis instance
    hba1c_value_counts_stratified_by_diabetes_type = (
        get_hba1c_value_counts_stratified_by_diabetes_type(calculate_kpis_instance=calculate_kpis)
    )

    # Admissions
    # Get attr names for KPIs 46-7
    admissions_kpi_attr_names = [
        calculate_kpis.kpi_name_registry.get_attribute_name(kpi) for kpi in range(46, 48)
    ]
    admissions_value_counts_absolute = get_admissions_value_counts_absolute(
        admissions_kpi_attr_names=admissions_kpi_attr_names,
        kpi_calculations_object=kpi_calculations_object["calculated_kpi_values"],
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
    pt_imd_value_counts_pct = convert_value_counts_dict_to_pct(pt_imd_value_counts)

    # Gather other context vars
    current_date = date.today()
    days_remaining_until_audit_end_date = (
        kpi_calculations_object["audit_end_date"] - current_date
    ).days
    current_quarter = retrieve_quarter_for_date(current_date)

    # Gather defaults for htmx partials pt level table
    default_pt_level_menu_text = TEXT["health_checks"]
    default_pt_level_menu_tab_selected = "health_checks"
    highlight = {f"{key}": key == default_pt_level_menu_tab_selected for key in TEXT.keys()}
    default_pt_level_table_headers, default_pt_level_table_data = get_pt_level_table_data(
        category="health_checks",
        calculate_kpis_object=calculate_kpis,
        kpi_calculations_object=kpi_calculations_object,
    )

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
                "data": {
                    "care": json.dumps(pt_characteristics_value_counts["care"]),
                    "died_or_transitioned": json.dumps(
                        pt_characteristics_value_counts["died_or_transitioned"]
                    ),
                    "comorbidity_and_testing": json.dumps(
                        pt_characteristics_value_counts["comorbidity_and_testing"]
                    ),
                }
            },
            "tx_regimen_value_counts_pct": {
                "no_eligible_patients": kpi_calculations_object["calculated_kpi_values"][
                    "kpi_1_total_eligible"
                ]["total_eligible"]
                == 0,
                "data": json.dumps(tx_regimen_value_counts_pct),
            },
            "glucose_monitoring_value_counts_pct": {
                "no_eligible_patients": kpi_calculations_object["calculated_kpi_values"][
                    "kpi_1_total_eligible"
                ]["total_eligible"]
                == 0,
                "data": json.dumps(glucose_monitoring_value_counts_pct),
            },
            "hcl_use_per_quarter_value_counts_pct": {
                "no_eligible_patients": kpi_calculations_object["calculated_kpi_values"][
                    "kpi_1_total_eligible"
                ]["total_eligible"]
                == 0,
                "data": json.dumps(hcl_use_per_quarter_value_counts_pct),
            },
            "care_at_diagnosis_value_count": {
                "no_eligible_patients": all(
                    [
                        care_at_diagnosis_value_counts_pct["coeliac_disease_screening"][
                            "total_eligible"
                        ]
                        == 0,
                        care_at_diagnosis_value_counts_pct["thyroid_disease_screening"][
                            "total_eligible"
                        ]
                        == 0,
                        care_at_diagnosis_value_counts_pct["carbohydrate_counting_education"][
                            "total_eligible"
                        ]
                        == 0,
                    ]
                ),
                "data": json.dumps(care_at_diagnosis_value_counts_pct),
            },
            "additional_care_processes_value_counts_pct": {
                "data": json.dumps(additional_care_processes_value_counts_pct),
            },
            "hc_completion_rate_value_counts_pct": {
                "data": json.dumps(hc_completion_rate_value_counts_pct),
            },
            "hba1c_value_counts": {
                "no_eligible_patients": kpi_calculations_object["calculated_kpi_values"][
                    "kpi_1_total_eligible"
                ]["total_eligible"]
                == 0,
                # No need to json-ify as data ready to render in template
                "data": hba1c_value_counts_stratified_by_diabetes_type,
            },
            "admissions_value_counts_absolute": {
                "no_eligible_patients": kpi_calculations_object["calculated_kpi_values"][
                    "kpi_1_total_eligible"
                ]["total_eligible"]
                == 0,
                "data": admissions_value_counts_absolute,
            },
            "pt_sex_value_counts_pct": {
                "data": json.dumps(pt_sex_value_counts_pct),
            },
            "pt_ethnicity_tree_map_data": {
                "no_eligible_patients": not pt_ethnicity_value_counts,
                "data": json.dumps(pt_ethnicity_value_counts),
                "parent_color_map": json.dumps(constants.ethnicities.ETHNICITY_PARENT_COLOR_MAP),
                "child_parent_map": json.dumps(constants.ethnicities.ETHNICITY_CHILD_PARENT_MAP),
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
        "default_table_data": {
            "headers": default_pt_level_table_headers,
            "row_data": default_pt_level_table_data,
            "ineligible_hover_reason": TEXT["health_checks"]["ineligible_hover_reason"],
        },
        # TODO: this should be an enum but we're currently not doing benchmarking so can update
        # at that point
        "aggregation_level": "pdu",
    }

    return render(request, template_name=template, context=context)
