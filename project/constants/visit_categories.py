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

CLINIC_VISIT_FIELDS = (  # These tend to be addressed at all clinic visits
    (VisitCategories.MEASUREMENT, MEASUREMENT_FIELDS),
    (VisitCategories.HBA1, HBA1_FIELDS),
    (VisitCategories.TREATMENT, TREATMENT_FIELDS),
    (VisitCategories.CGM, CGM_FIELDS),
    (VisitCategories.BP, BP_FIELDS),
)

ANNUAL_REVIEW_FIELDS = (  # These fields are only required once a year and tend to be done at the same time
    (VisitCategories.FOOT, FOOT_FIELDS),
    (VisitCategories.DECS, DECS_FIELDS),
    (VisitCategories.ACR, ACR_FIELDS),
    (VisitCategories.CHOLESTEROL, CHOLESTEROL_FIELDS),
    (VisitCategories.THYROID, THYROID_FIELDS),
    (VisitCategories.COELIAC, COELIAC_FIELDS),
    (VisitCategories.PSYCHOLOGY, PSYCHOLOGY_FIELDS),
    (VisitCategories.SMOKING, SMOKING_FIELDS),
    (VisitCategories.SICK_DAY, SICK_DAY_FIELDS),
    (VisitCategories.FLU, FLU_FIELDS),
)

EXTRA_VISIT_FIELDS = (  # These fields are not always part of annual review and are not always addressed in clinic visits
    (VisitCategories.DIETETIAN, DIETETIAN_FIELDS),
    (VisitCategories.PSYCHOLOGY, PSYCHOLOGY_FIELDS),
    (VisitCategories.HOSPITAL_ADMISSION, HOSPITAL_ADMISSION_FIELDS),
)


VISIT_CATEGORY_COLOURS = (
    (VisitCategories.HBA1, "rcpch_dark_grey"),
    (VisitCategories.MEASUREMENT, "rcpch_yellow"),
    (VisitCategories.TREATMENT, "rcpch_strong_green_light_tint1"),
    (VisitCategories.CGM, "rcpch_aqua_green_light_tint1"),
    (VisitCategories.BP, "rcpch_orange_light_tint1"),
    (VisitCategories.FOOT, "rcpch_gold"),
    (VisitCategories.DECS, "rcpch_vivid_green"),
    (VisitCategories.ACR, "rcpch_red_light_tint2"),
    (VisitCategories.CHOLESTEROL, "rcpch_orange_dark_tint"),
    (VisitCategories.THYROID, "rcpch_red_dark_tint"),
    (VisitCategories.COELIAC, "rcpch_purple_light_tint2"),
    (VisitCategories.PSYCHOLOGY, "rcpch_yellow_dark_tint"),
    (VisitCategories.SMOKING, "rcpch_strong_green_dark_tint"),
    (VisitCategories.DIETETIAN, "rcpch_aqua_green_dark_tint"),
    (VisitCategories.SICK_DAY, "rcpch_purple_dark_tint"),
    (VisitCategories.FLU, "rcpch_orange"),
    (VisitCategories.HOSPITAL_ADMISSION, "rcpch_red"),
)

VISIT_FIELD_FLAT_LIST = (
    MEASUREMENT_FIELDS
    + HBA1_FIELDS
    + TREATMENT_FIELDS
    + CGM_FIELDS
    + BP_FIELDS
    + FOOT_FIELDS
    + DECS_FIELDS
    + ACR_FIELDS
    + CHOLESTEROL_FIELDS
    + THYROID_FIELDS
    + COELIAC_FIELDS
    + PSYCHOLOGY_FIELDS
    + SMOKING_FIELDS
    + DIETETIAN_FIELDS
    + SICK_DAY_FIELDS
    + FLU_FIELDS
    + HOSPITAL_ADMISSION_FIELDS
)
