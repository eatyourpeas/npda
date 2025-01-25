"""Helper functions for dashboard views including calculations and data manipulation."""

# Python imports
from collections import Counter, defaultdict
import logging
from dateutil.relativedelta import relativedelta
from typing import Literal


from django.db.models import QuerySet, Count

from project.constants.ethnicities import ETHNICITIES
from project.constants.sex_types import SEX_TYPE
from project.constants.types.kpi_types import KPIRegistry
from project.npda.models.patient import Patient

from project.npda.kpi_class.kpis import CalculateKPIS
from project.npda.views.dashboard.template_data import *

# LOGGING
logger = logging.getLogger(__name__)


def add_number_of_figures_coloured_for_chart(
    value_counts_dict: dict[
        Literal["care", "died_or_transitioned", "comorbidity_and_testing"],
        dict[Literal["total_eligible", "total_ineligible", "pct"], int],
    ],
    n_figures_total: int = 5,
) -> dict[
    Literal["total_eligible", "total_ineligible", "pct", "figures_coloured"], int
]:
    """
    Add number of figures coloured to a value counts dict
    """
    # divisor is 100 / n_figures_total
    divisor = 100 / n_figures_total

    for category, vcs in value_counts_dict.items():
        for key, value in vcs.items():
            value_counts_dict[category][key]["figures_coloured"] = int(
                value["pct"] / divisor
            )

    return dict(value_counts_dict)


def get_total_eligible_pts_diabetes_type_value_counts(
    eligible_pts_queryset: QuerySet,
) -> dict:
    """Gets value counts dict for total eligible patients stratified by diabetes type

    Returns empty dict if no eligible pts."""

    eligible_pts_diabetes_type_counts = eligible_pts_queryset.values(
        "diabetes_type"
    ).annotate(count=Count("diabetes_type"))

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
    kpi_attr_names = [
        kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis
    ]

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
    for ix, kpi_values in enumerate(
        [kpi_32_1_values, kpi_32_2_values, kpi_32_3_values], start=1
    ):
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
    hba1c_vals = (
        calculate_kpis_instance.calculate_kpi_hba1c_vals_stratified_by_diabetes_type()
    )

    return hba1c_vals


def add_number_of_figures_coloured_for_chart(
    value_counts_dict: dict[
        Literal["care", "died_or_transitioned", "comorbidity_and_testing"],
        dict[Literal["total_eligible", "total_ineligible", "pct"], int],
    ],
    n_figures_total: int = 5,
) -> dict[
    Literal["total_eligible", "total_ineligible", "pct", "figures_coloured"], int
]:
    """
    Add number of figures coloured to a value counts dict
    """
    # divisor is 100 / n_figures_total
    divisor = 100 / n_figures_total

    for category, vcs in value_counts_dict.items():
        for key, value in vcs.items():
            value_counts_dict[category][key]["figures_coloured"] = int(
                value["pct"] / divisor
            )

    return dict(value_counts_dict)


def get_total_eligible_pts_diabetes_type_value_counts(
    eligible_pts_queryset: QuerySet,
) -> dict:
    """Gets value counts dict for total eligible patients stratified by diabetes type"""

    eligible_pts_diabetes_type_counts = eligible_pts_queryset.values(
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
    kpi_attr_names = [
        kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis
    ]

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


def get_total_eligible_pts_diabetes_type_value_counts(
    eligible_pts_queryset: QuerySet,
) -> dict:
    """Gets value counts dict for total eligible patients stratified by diabetes type"""

    eligible_pts_diabetes_type_counts = eligible_pts_queryset.values(
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
    kpi_attr_names = [
        kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis
    ]

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
    kpi_attr_names = [
        kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis
    ]

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
    kpi_attr_names = [
        kpi_name_registry.get_attribute_name(kpi) for kpi in relevant_kpis
    ]

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

    absolute_value_counts = {}
    for kpi_attr in admissions_kpi_attr_names:
        absolute_value_counts[kpi_attr] = kpi_calculations_object[kpi_attr][
            "total_passed"
        ]

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
        imd_map.get(item["index_of_multiple_deprivation_quintile"])
        for item in all_values
    )

    return (
        sex_counts,
        ethnicity_counts,
        imd_counts,
    )


def get_pt_level_table_data(
    category: Literal[
        "health_checks",
        "additional_care_processes",
        "care_at_diagnosis",
        "outcomes",
        "treatment",
    ],
    calculate_kpis_object: CalculateKPIS,
    kpi_calculations_object: dict,
) -> tuple[list[str], list[dict]]:
    """Get data for pt level table

    - headers
    - row_data

    where row_data is a list of dicts with the following example structure (keys are pt.pk):
        {
                11: {
                    nhs_number: str,
                    kpi_25_hba1c: bool,
                    kpi_26_bmi: bool,
                    kpi_27_thyroid: bool,
                    kpi_28_blood_pressure: bool | None,
                    kpi_29_urinary_albumin: bool | None,
                    kpi_30_retinal_screening: bool | None,
                    kpi_31_foot_examination: bool | None,
                    total: list[int, int],
                },
                12: {
                    nhs_number: str,
                    kpi_25_hba1c: bool,
                    kpi_26_bmi: bool,
                    kpi_27_thyroid: bool,
                    kpi_28_blood_pressure: bool | None,
                    kpi_29_urinary_albumin: bool | None,
                    kpi_30_retinal_screening: bool | None,
                    kpi_31_foot_examination: bool | None,
                    total: list[int, int],
                },
                ...
            }
    """

    kpi_attr_names = [
        calculate_kpis_object.kpi_name_registry.get_attribute_name(i)
        for i in KPI_CATEGORY_ATTR_MAP[category]
    ]

    if category == "health_checks":

        data = {}
        # First initialise the dict with all pts -> for health checks, this is KPI5 which can be found
        # via kpi_25's eligible pts
        for pt in kpi_calculations_object["calculated_kpi_values"]["kpi_25_hba1c"][
            "patient_querysets"
        ]["eligible"]:
            # Set all to None initially as updating as [True | False] if pt in [passed | failed]
            # querysets for each kpi -> if not in either, must mean they are ineligible (therefore None)
            data[pt.pk] = {kpi_attr_name: None for kpi_attr_name in kpi_attr_names}
            # Additional values we can calculate now
            if pt.nhs_number:
                data[pt.pk]["nhs_number"] = pt.nhs_number
            if pt.unique_reference_number:
                data[pt.pk]["nhs_number"] = pt.unique_reference_number
            else:
                data[pt.pk]["nhs_number"] = "Unknown"
            pt_is_gte_12yo = (
                pt.date_of_birth
                <= calculate_kpis_object.audit_start_date - relativedelta(years=12)
            )
            data[pt.pk]["is_gte_12yo"] = pt_is_gte_12yo
            # total = (passed / total)
            data[pt.pk]["total"] = [0, 7 if pt_is_gte_12yo else 3]

        # For each kpi, update the data dict with the pts that have passed and failed
        for kpi_attr_name in kpi_attr_names:

            kpi_pt_querysets = kpi_calculations_object["calculated_kpi_values"][
                kpi_attr_name
            ]["patient_querysets"]

            for pt in kpi_pt_querysets["passed"]:
                data[pt.pk]["total"][0] += 1
                data[pt.pk][kpi_attr_name] = True

            for pt in kpi_pt_querysets["failed"]:
                data[pt.pk][kpi_attr_name] = False

        # Finally add the headers. Need to add nhs_number, is_gte_12yo, and total to the headers
        headers = ["nhs_number", "is_gte_12yo"] + kpi_attr_names + ["total"]
        return headers, data

    elif category == "additional_care_processes":

        data = {}
        # Initialise with all eligible pts' pks as the key. Use kpi40 eligible
        # as this is KPI1 (all eligible pts)
        kpi_40_attr_name = calculate_kpis_object.kpi_name_registry.get_attribute_name(
            40
        )
        for pt in kpi_calculations_object["calculated_kpi_values"][kpi_40_attr_name][
            "patient_querysets"
        ]["eligible"]:
            # Set all to None initially as updating as [True | False] if pt in [passed | failed]
            # querysets for each kpi -> if not in either, must mean they are ineligible (therefore None)
            data[pt.pk] = {kpi_attr_name: None for kpi_attr_name in kpi_attr_names}
            # Additional values we can calculate now
            if pt.nhs_number:
                data[pt.pk]["nhs_number"] = pt.nhs_number
            if pt.unique_reference_number:
                data[pt.pk]["nhs_number"] = pt.unique_reference_number
            else:
                data[pt.pk]["nhs_number"] = "Unknown"

        # For each kpi, update the data dict with the pts that have passed and failed
        for kpi_attr_name in kpi_attr_names:

            kpi_pt_querysets = kpi_calculations_object["calculated_kpi_values"][
                kpi_attr_name
            ]["patient_querysets"]

            for pt in kpi_pt_querysets["passed"]:
                data[pt.pk][kpi_attr_name] = True

            for pt in kpi_pt_querysets["failed"]:
                data[pt.pk][kpi_attr_name] = False

        # Finally add the headers. Need to add nhs_number

        headers = ["nhs_number"] + kpi_attr_names
        return headers, data

    elif category == "care_at_diagnosis":
        data = {}

        for kpi_attr_name in kpi_attr_names:

            kpi_pt_querysets = kpi_calculations_object["calculated_kpi_values"][
                kpi_attr_name
            ]["patient_querysets"]

            # For each kpi_attribute's eligible pts, add to data dict
            for pt in kpi_pt_querysets["eligible"]:
                # If pt not already in, initialise with None for all kpi_attr_names
                if data.get(pt.pk) is None:
                    data[pt.pk] = {
                        kpi_attr_name: None for kpi_attr_name in kpi_attr_names
                    }
                    data[pt.pk]["nhs_number"] = pt.nhs_number

            for pt in kpi_pt_querysets["passed"]:
                data[pt.pk] = {kpi_attr_name: True}
                data[pt.pk]["nhs_number"] = pt.nhs_number

            for pt in kpi_pt_querysets["failed"]:
                data[pt.pk] = {kpi_attr_name: False}
                data[pt.pk]["nhs_number"] = pt.nhs_number

        # Finally add the headers. Need to add nhs_number
        headers = ["nhs_number"] + kpi_attr_names
        return headers, data

    elif category == "treatment":
        data = {}

        tx_vals = [
            "1-3 injections/day",
            "4+ injections/day",
            "Insulin pump",
            "1-3 injections + blood glucose lowering meds",
            "4+ injections + blood glucose lowering meds",
            "Insulin pump + blood glucose lowering meds",
            "Dietary management alone",
            "Dietary management + blood glucose lowering meds",
        ]
        tx_vals_attr_map = {
            attr_name: tx_val for attr_name, tx_val in zip(kpi_attr_names, tx_vals)
        }

        # Just need to iterate through one for initialisation as all denominators are kpi 1
        kpi_13_attr_name = calculate_kpis_object.kpi_name_registry.get_attribute_name(
            13
        )
        for pt in kpi_calculations_object["calculated_kpi_values"][kpi_13_attr_name][
            "patient_querysets"
        ]["eligible"]:
            # Only 1 column
            data[pt.pk] = {"value": None}
            # Additional values we can calculate now
            data[pt.pk]["nhs_number"] = pt.nhs_number

        for kpi_attr_name in kpi_attr_names:

            kpi_pt_querysets = kpi_calculations_object["calculated_kpi_values"][
                kpi_attr_name
            ]["patient_querysets"]

            # Only check pass as only 1 can be True
            for pt in kpi_pt_querysets["passed"]:
                data[pt.pk]["value"] = tx_vals_attr_map[kpi_attr_name]

        # Finally add the headers. Need to add nhs_number
        headers = ["nhs_number", "value"]

        return headers, data

    raise NotImplementedError(f"Category {category} not yet implemented")


def convert_value_counts_dict_to_pct(value_counts_dict: dict):
    """
    Convert a value counts dict to percentages
    """
    total = sum(value_counts_dict.values())

    value_counts_dict_pct = {}

    for key, value in value_counts_dict.items():
        value_counts_dict_pct[key] = int(value / total * 100)

    return value_counts_dict_pct
