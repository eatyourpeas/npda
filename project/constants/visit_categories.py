from enum import Enum

MEASUREMENT_FIELDS = ["height", "weight", "height_weight_observation_date"]
HBA1_FIELDS = ["hba1c", "hba1c_format", "hba1c_date"]
TREATMENT_FIELDS = ["treatment", "closed_loop_system"]
CGM_FIELDS = ["glucose_monitoring"]
BP_FIELDS = [
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
    "blood_pressure_observation_date",
]
FOOT_FIELDS = ["foot_examination_observation_date"]
DECS_FIELDS = ["retinal_screening_observation_date", "retinal_screening_result"]
ACR_FIELDS = [
    "albumin_creatinine_ratio",
    "albumin_creatinine_ratio_date",
    "albuminuria_stage",
]
CHOLESTEROL_FIELDS = ["total_cholesterol", "total_cholesterol_date"]
THYROID_FIELDS = ["thyroid_function_date", "thyroid_treatment_status"]
COELIAC_FIELDS = ["coeliac_screen_date", "gluten_free_diet"]
PSYCHOLOGY_FIELDS = [
    "psychological_screening_assessment_date",
    "psychological_additional_support_status",
]
SMOKING_FIELDS = ["smoking_status", "smoking_cessation_referral_date"]
DIETETIAN_FIELDS = [
    "carbohydrate_counting_level_three_education_date",
    "dietician_additional_appointment_offered",
    "dietician_additional_appointment_date",
]
SICK_DAY_FIELDS = ["ketone_meter_training", "sick_day_rules_training_date"]
FLU_FIELDS = ["flu_immunisation_recommended_date"]
HOSPITAL_ADMISSION_FIELDS = [
    "hospital_admission_date",
    "hospital_discharge_date",
    "hospital_admission_reason",
    "dka_additional_therapies",
    "hospital_admission_other",
]


class VisitCategories(Enum):
    MEASUREMENT = "Measurements"
    HBA1 = "HBA1c"
    TREATMENT = "Treatment"
    CGM = "CGM"
    BP = "BP"
    FOOT = "Foot Care"
    DECS = "DECS"
    ACR = "ACR"
    CHOLESTEROL = "Cholesterol"
    THYROID = "Thyroid"
    COELIAC = "Coeliac"
    PSYCHOLOGY = "Psychology"
    SMOKING = "Smoking"
    DIETETIAN = "Dietician"
    SICK_DAY = "Sick Day Rules"
    FLU = "Immunisation (flu)"
    HOSPITAL_ADMISSION = "Hospital Admission"

# TODO MRB: merge all these to make it less likely we forget to update one

VISIT_FIELDS = (
    (VisitCategories.MEASUREMENT, MEASUREMENT_FIELDS),
    (VisitCategories.HBA1, HBA1_FIELDS),
    (VisitCategories.TREATMENT, TREATMENT_FIELDS),
    (VisitCategories.CGM, CGM_FIELDS),
    (VisitCategories.BP, BP_FIELDS),
    (VisitCategories.FOOT, FOOT_FIELDS),
    (VisitCategories.DECS, DECS_FIELDS),
    (VisitCategories.ACR, ACR_FIELDS),
    (VisitCategories.CHOLESTEROL, CHOLESTEROL_FIELDS),
    (VisitCategories.THYROID, THYROID_FIELDS),
    (VisitCategories.COELIAC, COELIAC_FIELDS),
    (VisitCategories.PSYCHOLOGY, PSYCHOLOGY_FIELDS),
    (VisitCategories.SMOKING, SMOKING_FIELDS),
    (VisitCategories.DIETETIAN, DIETETIAN_FIELDS),
    (VisitCategories.SICK_DAY, SICK_DAY_FIELDS),
    (VisitCategories.FLU, FLU_FIELDS),
    (VisitCategories.HOSPITAL_ADMISSION, HOSPITAL_ADMISSION_FIELDS),
)

VISIT_CATEGORY_COLOURS = {
    VisitCategories.MEASUREMENT: "rcpch_yellow",
    VisitCategories.HBA1: "rcpch_dark_grey",
    VisitCategories.TREATMENT: "rcpch_strong_green_light_tint1",
    VisitCategories.CGM: "rcpch_aqua_green_light_tint1",
    VisitCategories.BP: "rcpch_orange_light_tint1",
    VisitCategories.FOOT: "rcpch_gold",
    VisitCategories.DECS: "rcpch_vivid_green",
    VisitCategories.ACR: "rcpch_red_light_tint2",
    VisitCategories.CHOLESTEROL: "rcpch_orange_dark_tint",
    VisitCategories.THYROID: "rcpch_red_dark_tint",
    VisitCategories.COELIAC: "rcpch_purple_light_tint2",
    VisitCategories.PSYCHOLOGY: "rcpch_yellow_dark_tint",
    VisitCategories.SMOKING: "rcpch_strong_green_dark_tint",
    VisitCategories.DIETETIAN: "rcpch_aqua_green_dark_tint",
    VisitCategories.SICK_DAY: "rcpch_pink_light_tint2",
    VisitCategories.FLU: "rcpch_orange",
    VisitCategories.HOSPITAL_ADMISSION: "rcpch_strong_green_dark_tint",
}

VISIT_TABS = (
    ("Routine Measurements", [
        VisitCategories.MEASUREMENT,
        VisitCategories.HBA1,
        VisitCategories.TREATMENT,
        VisitCategories.CGM,
        VisitCategories.BP
    ]),
    ("Annual Review", [
        VisitCategories.FOOT,
        VisitCategories.DECS,
        VisitCategories.ACR,
        VisitCategories.CHOLESTEROL,
        VisitCategories.THYROID,
        VisitCategories.COELIAC,
        VisitCategories.PSYCHOLOGY,
        VisitCategories.SMOKING,
        VisitCategories.DIETETIAN,
        VisitCategories.SICK_DAY,
        VisitCategories.FLU
    ]),
    ("Inpatient Entry", [
        VisitCategories.HOSPITAL_ADMISSION
    ])
)