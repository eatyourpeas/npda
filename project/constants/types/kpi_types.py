# Object types
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Dict, Literal, Optional, Union

from django.db.models import QuerySet

from project.npda.models import Patient


@dataclass
class KPIResult:
    """
    Example would be:

    `return_patient_querysets` == False
    {
        'total_eligible': 100,
        'total_ineligible': 50,
        'total_passed': 75,
        'total_failed': 25,
        'patient_querysets': None
    }

    `return_patient_querysets` == True
    {
        'total_eligible': 100,
        'total_ineligible': 50,
        'total_passed': 75,
        'total_failed': 25,
        'patient_querysets': {
            'eligible': <QuerySet[Patient]>,
            'ineligible': <QuerySet[Patient]>,
            'passed': <QuerySet[Patient]>,
            'failed': <QuerySet[Patient]>,
        }
    }
    """

    total_eligible: int
    total_ineligible: int
    total_passed: Union[int | None]  # E.g. KPIs 1-12 would be None as counts
    total_failed: Union[int | None]  # E.g. KPIs 1-12 would be None as counts
    kpi_label: str = "KPI Name not found"
    patient_querysets: Union[Dict[str, QuerySet[Patient]], None] = None


@dataclass
class IndividualPtKPIResults:
    """Type for individual patient KPI results.

    KPIS 25+26 always have values
    KPIS 27-31 will be None for pts >= 12yo
    """

    kpi_25_hba1c: bool
    kpi_26_bmi: bool
    kpi_27_thyroid_screen: bool
    kpi_28_blood_pressure: Optional[bool]
    kpi_29_urinary_albumin: Optional[bool]
    kpi_30_retinal_screening: Optional[bool]
    kpi_31_foot_examination: Optional[bool]

    def get_total_passed(self)->int:
        return sum(
            value for value in asdict(self).values() if value is not None
        )


@dataclass
class IndividualPtKPICalculationsObject:
    """A single record for individual patient's KPI calculations."""

    calculation_datetime: datetime
    audit_start_date: date
    audit_end_date: date
    nhs_number: str
    gte_12yo: bool
    diagnosed_in_period: bool
    died_in_period: bool
    transfer_in_period: bool
    kpi_results: IndividualPtKPIResults
    total_passed: int = None  # Default value to be set later
    expected_total: Literal[3, 7] = None  # Default value to be set later

    def __post_init__(self):

        # Set total_passed
        self.total_passed = self.kpi_results.get_total_passed()

        # Set expected_total based on gte_12yo
        self.expected_total = 7 if self.gte_12yo else 3


@dataclass
class KPICalculationsObject:
    calculation_datetime: datetime
    audit_start_date: date
    audit_end_date: date
    total_patients_count: int
    calculated_kpi_values: Dict[
        str,
        KPIResult,
    ]


"""
Hard coding these for simplicty and readability

KPIS
1-12
    - used as denominators for subsequent
13-20
    - treatment regimen
21-23
    - glucose monitoring
24
    - Hybrid closed loop system (HCL)
25-32
    - 7 key processes
33-40
    - additional processes
41-43
    - care at diagnosis
44-49
    - outcomes
"""
KPI_ATTRIBUTE_LABEL_MAP = {
    1: {
        "attribute_name": "kpi_1_total_eligible",
        "rendered_label": "Total number of eligible patients",
    },
    2: {
        "attribute_name": "kpi_2_total_new_diagnoses",
        "rendered_label": "Total number of new diagnoses within the audit period",
    },
    3: {
        "attribute_name": "kpi_3_total_t1dm",
        "rendered_label": "Total number of eligible patients with Type 1 diabetes",
    },
    4: {
        "attribute_name": "kpi_4_total_t1dm_gte_12yo",
        "rendered_label": "Number of patients aged 12+ with Type 1 diabetes",
    },
    5: {
        "attribute_name": "kpi_5_total_t1dm_complete_year",
        "rendered_label": "Total number of patients with T1DM who have completed a year of care",
    },
    6: {
        "attribute_name": "kpi_6_total_t1dm_complete_year_gte_12yo",
        "rendered_label": "Total number of patients with T1DM who have completed a year of care and are aged 12 or older",
    },
    7: {
        "attribute_name": "kpi_7_total_new_diagnoses_t1dm",
        "rendered_label": "Total number of new diagnoses of T1DM",
    },
    8: {
        "attribute_name": "kpi_8_total_deaths",
        "rendered_label": "Number of patients who died within audit period",
    },
    9: {
        "attribute_name": "kpi_9_total_service_transitions",
        "rendered_label": "Number of patients who transitioned/left service within audit period",
    },
    10: {
        "attribute_name": "kpi_10_total_coeliacs",
        "rendered_label": "Total number of coeliacs",
    },
    11: {
        "attribute_name": "kpi_11_total_thyroids",
        "rendered_label": "Number of patients with thyroid disease",
    },
    12: {
        "attribute_name": "kpi_12_total_ketone_test_equipment",
        "rendered_label": "Number of patients with ketone test equipment",
    },
    13: {
        "attribute_name": "kpi_13_one_to_three_injections_per_day",
        "rendered_label": "Number of patients on one to three injections per day",
    },
    14: {
        "attribute_name": "kpi_14_four_or_more_injections_per_day",
        "rendered_label": "Number of patients on four or more injections per day",
    },
    15: {
        "attribute_name": "kpi_15_insulin_pump",
        "rendered_label": "Number of patients on insulin pump",
    },
    16: {
        "attribute_name": "kpi_16_one_to_three_injections_plus_other_medication",
        "rendered_label": "Number of patients on one to three injections plus other medication",
    },
    17: {
        "attribute_name": "kpi_17_four_or_more_injections_plus_other_medication",
        "rendered_label": "Number of patients on four or more injections plus other medication",
    },
    18: {
        "attribute_name": "kpi_18_insulin_pump_plus_other_medication",
        "rendered_label": "Number of patients on insulin pump plus other medication",
    },
    19: {
        "attribute_name": "kpi_19_dietary_management_alone",
        "rendered_label": "Number of patients on dietary management alone",
    },
    20: {
        "attribute_name": "kpi_20_dietary_management_plus_other_medication",
        "rendered_label": "Number of patients on dietary management plus other medication",
    },
    21: {
        "attribute_name": "kpi_21_flash_glucose_monitor",
        "rendered_label": "Number of patients on flash glucose monitor",
    },
    22: {
        "attribute_name": "kpi_22_real_time_cgm_with_alarms",
        "rendered_label": "Number of patients on real-time CGM with alarms",
    },
    23: {
        "attribute_name": "kpi_23_type1_real_time_cgm_with_alarms",
        "rendered_label": "Number of patients on Type 1 real-time CGM with alarms",
    },
    24: {
        "attribute_name": "kpi_24_hybrid_closed_loop_system",
        "rendered_label": "Number of patients on hybrid closed loop system",
    },
    25: {
        "attribute_name": "kpi_25_hba1c",
        "rendered_label": "Number of patients with HbA1c",
    },
    26: {
        "attribute_name": "kpi_26_bmi",
        "rendered_label": "Number of patients with BMI",
    },
    27: {
        "attribute_name": "kpi_27_thyroid_screen",
        "rendered_label": "Number of patients with thyroid screen",
    },
    28: {
        "attribute_name": "kpi_28_blood_pressure",
        "rendered_label": "Number of patients with blood pressure",
    },
    29: {
        "attribute_name": "kpi_29_urinary_albumin",
        "rendered_label": "Number of patients with urinary albumin",
    },
    30: {
        "attribute_name": "kpi_30_retinal_screening",
        "rendered_label": "Number of patients with retinal screening",
    },
    31: {
        "attribute_name": "kpi_31_foot_examination",
        "rendered_label": "Number of patients with foot examination",
    },
    321: {
        "attribute_name": "kpi_32_1_health_check_completion_rate",
        "rendered_label": "Care processes completion rate",
    },
    322: {
        "attribute_name": "kpi_32_2_health_check_lt_12yo",
        "rendered_label": "Care processes in patients < 12 years old",
    },
    323: {
        "attribute_name": "kpi_32_3_health_check_gte_12yo",
        "rendered_label": "Care processes in patients ≥ 12 years old",
    },
    33: {
        "attribute_name": "kpi_33_hba1c_4plus",
        "rendered_label": "Number of patients with 4 or more HbA1c measurements",
    },
    34: {
        "attribute_name": "kpi_34_psychological_assessment",
        "rendered_label": "Number of patients offered a psychological assessment",
    },
    35: {
        "attribute_name": "kpi_35_smoking_status_screened",
        "rendered_label": "Number of patients asked about smoking status",
    },
    36: {
        "attribute_name": "kpi_36_referral_to_smoking_cessation_service",
        "rendered_label": "Number of patients referred to a smoking cessation service",
    },
    37: {
        "attribute_name": "kpi_37_additional_dietetic_appointment_offered",
        "rendered_label": "Number of patients offered an additional dietetic appointment",
    },
    38: {
        "attribute_name": "kpi_38_patients_attending_additional_dietetic_appointment",
        "rendered_label": "Number of patients attending an additional dietetic appointment",
    },
    39: {
        "attribute_name": "kpi_39_influenza_immunisation_recommended",
        "rendered_label": "Number of patients recommended influenza immunisation",
    },
    40: {
        "attribute_name": "kpi_40_sick_day_rules_advice",
        "rendered_label": "Number of patients given sick day rules advice",
    },
    41: {
        "attribute_name": "kpi_41_coeliac_disease_screening",
        "rendered_label": "Number of patients with coeliac disease screening",
    },
    42: {
        "attribute_name": "kpi_42_thyroid_disease_screening",
        "rendered_label": "Number of patients with thyroid disease screening",
    },
    43: {
        "attribute_name": "kpi_43_carbohydrate_counting_education",
        "rendered_label": "Number of patients with carbohydrate counting education",
    },
    44: {
        "attribute_name": "kpi_44_mean_hba1c",
        "rendered_label": "Mean HbA1c",
    },
    45: {
        "attribute_name": "kpi_45_median_hba1c",
        "rendered_label": "Median HbA1c",
    },
    46: {
        "attribute_name": "kpi_46_number_of_admissions",
        "rendered_label": "Number of admissions",
    },
    47: {
        "attribute_name": "kpi_47_number_of_dka_admissions",
        "rendered_label": "Number of DKA admissions",
    },
    48: {
        "attribute_name": "kpi_48_required_additional_psychological_support",
        "rendered_label": "Number of patients requiring additional psychological support",
    },
    49: {
        "attribute_name": "kpi_49_albuminuria_present",
        "rendered_label": "Number of patients with albuminuria",
    },
}


@dataclass
class KPINames:
    attribute_name: str  # e.g. kpi_32_1_health_check_completion_rate
    rendered_label: str  # e.g. Care Processes Completion Rate


class KPIRegistry:
    """Makes it easier to get attribute names and rendered labels for KPIs,
    hardcoded above.

    Usage:

    kpi_registry.get_kpi(323)
        -> KPINames(
            attribute_name='kpi_32_3_health_check_gte_12yo',
            rendered_label='Care processes in patients ≥ 12 years old'
        )

    kpi_registry.get_attribute_name(323)
        -> 'kpi_32_3_health_check_gte_12yo'

    kpi_registry.get_rendered_label(323)
        -> 'Care processes in patients ≥ 12 years old'
    """

    def __init__(self, kpi_data: Dict[int, Dict[str, str]]):
        self.kpi_map = {
            number: KPINames(data["attribute_name"], data["rendered_label"])
            for number, data in kpi_data.items()
        }

    def get_kpi(self, number: int) -> KPINames:
        return self.kpi_map.get(number)

    def get_attribute_name(self, number: int) -> str:
        kpi = self.get_kpi(number)
        return kpi.attribute_name if kpi else None

    def get_rendered_label(self, number: int) -> str:
        kpi = self.get_kpi(number)
        return kpi.rendered_label if kpi else None


# Initialise registry
kpi_registry = KPIRegistry(KPI_ATTRIBUTE_LABEL_MAP)
