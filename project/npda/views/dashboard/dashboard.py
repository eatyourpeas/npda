# Python imports
from collections import Counter, defaultdict
import json
import logging
from dateutil.relativedelta import relativedelta
from datetime import date
from typing import Literal


# Django imports
from django.apps import apps
from django.contrib import messages
from django.shortcuts import render
from django.db.models import QuerySet, Count

from project.constants.diabetes_types import DIABETES_TYPES
from project.constants.ethnicities import ETHNICITIES
from project.constants.sex_types import SEX_TYPE
from project.constants.types.kpi_types import KPIRegistry
from project.npda.general_functions.quarter_for_date import retrieve_quarter_for_date
from project.npda.models.paediatric_diabetes_unit import (
    PaediatricDiabetesUnit as PaediatricDiabetesUnitClass,
)
from project.npda.models.patient import Patient


# HTMX imports
from project.npda.general_functions.session import (
    refresh_session_object_synchronously,
)
from project.npda.kpi_class.kpis import CalculateKPIS

# RCPCH imports
from project.npda.views.decorators import login_and_otp_required

# LOGGING
logger = logging.getLogger(__name__)

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
    if request.htmx:
        template = "dashboard/dashboard_base.html"
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

    # 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
    # 🚨 TODO SHOULD BE REMOVED, JUST DURING DEV  🚨
    # 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
    """Temporary util to set some seeded patients attrs manually
    
    KPI7
        to be eligible for kpi 7 (T1DM diagnosed
        during the audit period) which is denominator for kpis 41-43.

        This is because the default behaviour of the `PatientFactory` .build method (used in the
        csv seeder) is to choose a random diabetes_diagnosis between the pt's DoB and audit_start_date.
    
    """
    _ = 10
    logger.error(f"🔥 Setting first {_} patients to be eligible for KPI 7")
    to_set_kpi_7_eligible = calculate_kpis.patients[:_]
    for pt in to_set_kpi_7_eligible:
        pt.diagnosis_date = calculate_kpis.audit_start_date + relativedelta(months=1)
        pt.diabetes_type = DIABETES_TYPES[0][0]
        pt.save()
        logger.warning(f"Succesfully set {pt} to be eligible for KPI 7")
    # 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
    # 🚨 TODO SHOULD BE REMOVED, JUST DURING DEV  🚨
    # 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨

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
    print(f"{admissions_value_counts_absolute=}")

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
            "tx_regimen_value_counts_pct": {
                "data": json.dumps(tx_regimen_value_counts_pct),
            },
            "glucose_monitoring_value_counts_pct": {
                "data": json.dumps(glucose_monitoring_value_counts_pct),
            },
            "hcl_use_per_quarter_value_counts_pct": {
                "data": json.dumps(hcl_use_per_quarter_value_counts_pct),
            },
            "care_at_diagnosis_value_count": {
                "data": json.dumps(care_at_diagnosis_value_counts_pct),
            },
            "additional_care_processes_value_counts_pct": {
                "data": json.dumps(additional_care_processes_value_counts_pct),
            },
            "hc_completion_rate_value_counts_pct": {
                "data": json.dumps(hc_completion_rate_value_counts_pct),
            },
            "hba1c_value_counts": {
                # No need to json-ify as data ready to render in template
                "data": hba1c_value_counts_stratified_by_diabetes_type,
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


def get_hba1c_value_counts_stratified_by_diabetes_type(
    calculate_kpis_instance: CalculateKPIS,
) -> dict:
    """Gets the data for plotting on the chart.

    The KPI class does not stratify by diabetes type so we need to do this here."""

    # Get the query sets (the hba1c value)
    hba1c_vals = calculate_kpis_instance.calculate_kpi_hba1c_vals_stratified_by_diabetes_type()

    return hba1c_vals


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


def get_total_eligible_pts_diabetes_type_value_counts(
    eligible_pts_queryset: QuerySet,
) -> dict:
    """Gets value counts dict for total eligible patients stratified by diabetes type"""

    eligible_pts_diabetes_type_counts = eligible_pts_queryset.values("diabetes_type").annotate(
        count=Count("diabetes_type")
    )
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


def get_total_eligible_pts_diabetes_type_value_counts(
    eligible_pts_queryset: QuerySet,
) -> dict:
    """Gets value counts dict for total eligible patients stratified by diabetes type"""

    eligible_pts_diabetes_type_counts = eligible_pts_queryset.values("diabetes_type").annotate(
        count=Count("diabetes_type")
    )
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


def get_tx_regimen_value_counts_pcts(
    kpi_name_registry: KPIRegistry,
    kpi_calculations_object: dict,
) -> dict:
    """Get value counts with pcts for treatment regimen KPIs

    - treatment_regimen (KPIs 13-15)
    """
    # Get attribute names and labels
    relevant_kpis = [13, 14, 15]
    # Labels used for bar chart htmx partial
    labels = [
        "1-3 insulin injections per day",
        "Multiple injections per day",
        "Insulin pump",
    ]
    kpi_attr_names = [kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis]

    value_counts = defaultdict(lambda: {"count": 0, "total": 0, "pct": 0})

    for label, kpi_attr in zip(labels, kpi_attr_names):
        total_eligible = kpi_calculations_object[kpi_attr]["total_eligible"]
        total_ineligible = kpi_calculations_object[kpi_attr]["total_ineligible"]

        # Need these keys for bar chart partial
        value_counts[kpi_attr]["count"] = total_eligible
        value_counts[kpi_attr]["total"] = total_eligible + total_ineligible
        value_counts[kpi_attr]["pct"] = (
            int(total_eligible / value_counts[kpi_attr]["total"] * 100)
            if value_counts[kpi_attr]["total"] > 0
            else 0
        )
        value_counts[kpi_attr]["label"] = label

    return dict(value_counts)


def get_glucose_monitoring_value_counts_pcts(
    kpi_name_registry: KPIRegistry,
    kpi_calculations_object: dict,
) -> dict:
    """Get value counts with pcts for glucose monitoring KPIs:

    - glucose_monitoring (KPIs 21-23)
    """
    # Get attribute names and labels
    relevant_kpis = [21, 22, 23]
    kpi_attr_names = [kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis]

    # Labels used for bar chart htmx partial
    labels = [
        "Flash glucose monitor",
        "Continuous glucose monitor with alarms",
        "T1DM and Continuous glucose monitor with alarms",
    ]

    value_counts = defaultdict(lambda: {"count": 0, "total": 0, "pct": 0})

    for label, kpi_attr in zip(labels, kpi_attr_names):
        total_eligible = kpi_calculations_object[kpi_attr]["total_eligible"]
        total_ineligible = kpi_calculations_object[kpi_attr]["total_ineligible"]

        value_counts[kpi_attr]["count"] = total_eligible
        value_counts[kpi_attr]["total"] = total_eligible + total_ineligible
        value_counts[kpi_attr]["pct"] = (
            int(total_eligible / value_counts[kpi_attr]["total"] * 100)
            if value_counts[kpi_attr]["total"] > 0
            else 0
        )
        value_counts[kpi_attr]["label"] = label

    return dict(value_counts)


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


def get_additional_care_processes_value_counts(
    additional_care_processes_kpi_attr_names: list[str],
    kpi_calculations_object: dict,
) -> dict:
    """Denominator already is CYP with T1DM (with completed year of care)

    So can just use values from kpi calculator. Just need to restructure and calc pct"""

    labels = [
        "HbA1c 4+",
        "Psychological Assessment",
        "Smoking status screened",
        "Referral to smoking cessation service",
        "Additional dietetic appointment offered",
        "Patients attending additional dietetic appointment",
        "Influenza immunisation reccommended",
        "Sick day rules advice",
    ]

    value_counts = defaultdict(lambda: {"count": 0, "total": 0, "pct": 0})

    for ix, kpi_attr in enumerate(additional_care_processes_kpi_attr_names):
        total_eligible = kpi_calculations_object[kpi_attr]["total_eligible"]
        total_ineligible = kpi_calculations_object[kpi_attr]["total_ineligible"]

        # Need all 3 for front end chart
        value_counts[kpi_attr]["count"] = total_eligible
        value_counts[kpi_attr]["total"] = total_eligible + total_ineligible
        value_counts[kpi_attr]["pct"] = (
            round(total_eligible / value_counts[kpi_attr]["total"] * 100, 1)
            if value_counts[kpi_attr]["total"] > 0
            else 0
        )
        value_counts[kpi_attr]["label"] = labels[ix]

    return dict(value_counts)


def get_admissions_value_counts_absolute(
    admissions_kpi_attr_names: list[str],
    kpi_calculations_object=dict,
):
    """Can simply get the .total_passed value for the absolute counts"""
    labels = ["Total", "With DKA"]

    absolute_value_counts = defaultdict(int)
    for ix, kpi_attr in enumerate(admissions_kpi_attr_names):
        absolute_value_counts[labels[ix]] = kpi_calculations_object[kpi_attr]["total_passed"]
    
    return absolute_value_counts
        


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
