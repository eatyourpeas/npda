import pandas as pd

CSV_HEADINGS = (
    # Patient
    {"heading": "NHS Number", "model_field": "nhs_number", "model": "Patient"},
    {"heading": "Date of Birth", "model_field": "date_of_birth", "model": "Patient"},
    {
        "heading": "Postcode of usual address",
        "model_field": "postcode",
        "model": "Patient",
    },
    {"heading": "Stated gender", "model_field": "sex", "model": "Patient"},
    {"heading": "Ethnic Category", "model_field": "ethnicity", "model": "Patient"},
    {"heading": "Diabetes Type", "model_field": "diabetes_type", "model": "Patient"},
    {
        "heading": "Date of Diabetes Diagnosis",
        "model_field": "diagnosis_date",
        "model": "Patient",
    },
    {
        "heading": "Date of leaving service",
        "model_field": "date_leaving_service",
        "model": "Transfer",
    },
    {
        "heading": "Reason for leaving service",
        "model_field": "reason_leaving_service",
        "model": "Transfer",
    },
    {"heading": "Death Date", "model_field": "death_date", "model": "Patient"},
    {
        "heading": "GP Practice Code",
        "model_field": "gp_practice_ods_code",
        "model": "Patient",
    },
    {"heading": "PDU Number", "model_field": "pdu", "model": "Patient"},
    # Visit
    {
        "heading": "Visit/Appointment Date",
        "model_field": "visit_date",
        "model": "Visit",
    },
    {"heading": "Patient Height (cm)", "model_field": "height", "model": "Visit"},
    {"heading": "Patient Weight (kg)", "model_field": "weight", "model": "Visit"},
    {
        "heading": "Observation Date (Height and weight)",
        "model_field": "height_weight_observation_date",
        "model": "Visit",
    },
    {"heading": "Hba1c Value", "model_field": "hba1c", "model": "Visit"},
    {"heading": "HbA1c result format", "model_field": "hba1c_format", "model": "Visit"},
    {
        "heading": "Observation Date: Hba1c Value",
        "model_field": "hba1c_date",
        "model": "Visit",
    },
    {
        "heading": "Diabetes Treatment at time of Hba1c measurement",
        "model_field": "treatment",
        "model": "Visit",
    },
    {
        "heading": "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
        "model_field": "closed_loop_system",
        "model": "Visit",
    },
    {
        "heading": "At the time of HbA1c measurement, in addition to standard blood glucose monitoring (SBGM), was the patient using any other method of glucose monitoring?",
        "model_field": "glucose_monitoring",
        "model": "Visit",
    },
    {
        "heading": "Systolic Blood Pressure",
        "model_field": "systolic_blood_pressure",
        "model": "Visit",
    },
    {
        "heading": "Diastolic Blood pressure",
        "model_field": "diastolic_blood_pressure",
        "model": "Visit",
    },
    {
        "heading": "Observation Date (Blood Pressure)",
        "model_field": "blood_pressure_observation_date",
        "model": "Visit",
    },
    {
        "heading": "Foot Assessment / Examination Date",
        "model_field": "foot_examination_observation_date",
        "model": "Visit",
    },
    {
        "heading": "Retinal Screening date",
        "model_field": "retinal_screening_observation_date",
        "model": "Visit",
    },
    {
        "heading": "Retinal Screening Result",
        "model_field": "retinal_screening_result",
        "model": "Visit",
    },
    {
        "heading": "Urinary Albumin Level (ACR)",
        "model_field": "albumin_creatinine_ratio",
        "model": "Visit",
    },
    {
        "heading": "Observation Date: Urinary Albumin Level",
        "model_field": "albumin_creatinine_ratio_date",
        "model": "Visit",
    },
    {
        "heading": "Albuminuria Stage",
        "model_field": "albuminuria_stage",
        "model": "Visit",
    },
    {
        "heading": "Total Cholesterol Level (mmol/l)",
        "model_field": "total_cholesterol",
        "model": "Visit",
    },
    {
        "heading": "Observation Date: Total Cholesterol Level",
        "model_field": "total_cholesterol_date",
        "model": "Visit",
    },
    {
        "heading": "Observation Date: Thyroid Function",
        "model_field": "thyroid_function_date",
        "model": "Visit",
    },
    {
        "heading": "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
        "model_field": "thyroid_treatment_status",
        "model": "Visit",
    },
    {
        "heading": "Observation Date: Coeliac Disease Screening",
        "model_field": "coeliac_screen_date",
        "model": "Visit",
    },
    {
        "heading": "Has the patient been recommended a Gluten-free diet?",
        "model_field": "gluten_free_diet",
        "model": "Visit",
    },
    {
        "heading": "Observation Date - Psychological Screening Assessment",
        "model_field": "psychological_screening_assessment_date",
        "model": "Visit",
    },
    {
        "heading": "Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?",
        "model_field": "psychological_additional_support_status",
        "model": "Visit",
    },
    {
        "heading": "Does the patient smoke?",
        "model_field": "smoking_status",
        "model": "Visit",
    },
    {
        "heading": "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
        "model_field": "smoking_cessation_referral_date",
        "model": "Visit",
    },
    {
        "heading": "Date of Level 3 carbohydrate counting education received",
        "model_field": "carbohydrate_counting_level_three_education_date",
        "model": "Visit",
    },
    {
        "heading": "Was the patient offered an additional appointment with a paediatric dietitian?",
        "model_field": "dietician_additional_appointment_offered",
        "model": "Visit",
    },
    {
        "heading": "Date of additional appointment with dietitian",
        "model_field": "dietician_additional_appointment_date",
        "model": "Visit",
    },
    {
        "heading": "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
        "model_field": "ketone_meter_training",
        "model": "Visit",
    },
    {
        "heading": "Date that influenza immunisation was recommended",
        "model_field": "flu_immunisation_recommended_date",
        "model": "Visit",
    },
    {
        "heading": "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
        "model_field": "sick_day_rules_training_date",
        "model": "Visit",
    },
    {
        "heading": "Start date (Hospital Provider Spell)",
        "model_field": "hospital_admission_date",
        "model": "Visit",
    },
    {
        "heading": "Discharge date (Hospital provider spell)",
        "model_field": "hospital_discharge_date",
        "model": "Visit",
    },
    {
        "heading": "Reason for admission",
        "model_field": "hospital_admission_reason",
        "model": "Visit",
    },
    {
        "heading": "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
        "model_field": "dka_additional_therapies",
        "model": "Visit",
    },
    {
        "heading": "Only complete if OTHER selected: Reason for admission (free text)",
        "model_field": "hospital_admission_other",
        "model": "Visit",
    },
)

ALL_DATES = [
    "Date of Birth",
    "Date of Diabetes Diagnosis",
    "Date of leaving service",
    "Death Date",
    "Visit/Appointment Date",
    "Observation Date (Height and weight)",
    "Observation Date: Hba1c Value",
    "Observation Date (Blood Pressure)",
    "Foot Assessment / Examination Date",
    "Retinal Screening date",
    "Observation Date: Urinary Albumin Level",
    "Observation Date: Total Cholesterol Level",
    "Observation Date: Thyroid Function",
    "Observation Date: Coeliac Disease Screening",
    "Observation Date - Psychological Screening Assessment",
    "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    "Date of Level 3 carbohydrate counting education received",
    "Date of additional appointment with dietitian",
    "Date that influenza immunisation was recommended",
    "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
    "Start date (Hospital Provider Spell)",
    "Discharge date (Hospital provider spell)",
]

ALL_VISIT_DATES = [
    ("visit_date", "Visit/Appointment Date"),
    ("height_weight_observation_date", "Observation Date (Height and weight)"),
    ("hba1c_date", "Observation Date: Hba1c Value"),
    ("blood_pressure_observation_date", "Observation Date (Blood Pressure)"),
    ("foot_examination_observation_date", "Foot Assessment / Examination Date"),
    ("retinal_screening_observation_date", "Retinal Screening date"),
    ("albumin_creatinine_ratio_date", "Observation Date: Urinary Albumin Level"),
    ("total_cholesterol_date", "Observation Date: Total Cholesterol Level"),
    ("thyroid_function_date", "Observation Date: Thyroid Function"),
    ("coeliac_screen_date", "Observation Date: Coeliac Disease Screening"),
    (
        "psychological_screening_assessment_date",
        "Observation Date - Psychological Screening Assessment",
    ),
    (
        "smoking_cessation_referral_date",
        "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    ),
    (
        "carbohydrate_counting_level_three_education_date",
        "Date of Level 3 carbohydrate counting education received",
    ),
    (
        "dietician_additional_appointment_date",
        "Date of additional appointment with dietitian",
    ),
    (
        "flu_immunisation_recommended_date",
        "Date that influenza immunisation was recommended",
    ),
    (
        "sick_day_rules_training_date",
        "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
    ),
    ("hospital_admission_date", "Start date (Hospital Provider Spell)"),
    ("hospital_discharge_date", "Discharge date (Hospital provider spell)"),
]

CSV_DATA_TYPES_MINUS_DATES = {
    "NHS Number": "str",
    "Postcode of usual address": "str",
    "Stated gender": "Int8",
    "Ethnic Category": "str",  # choices are all capital letters
    "Diabetes Type": "Int8",
    "Reason for leaving service": "Int8",
    "GP Practice Code": "str",
    "PDU Number": "str",
    "Patient Height (cm)": "float64",
    "Patient Weight (kg)": "float64",
    "Hba1c Value": "float64",
    "HbA1c result format": "Int8",
    "Diabetes Treatment at time of Hba1c measurement": "Int8",
    "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?": "Int8",
    "At the time of HbA1c measurement, in addition to standard blood glucose monitoring (SBGM), was the patient using any other method of glucose monitoring?": "Int8",
    "Systolic Blood Pressure": "Int8",
    "Diastolic Blood pressure": "Int8",
    "Retinal Screening Result": "Int8",
    "Urinary Albumin Level (ACR)": "float64",
    "Albuminuria Stage": "Int8",
    "Total Cholesterol Level (mmol/l)": "float64",
    "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?": "Int8",
    "Has the patient been recommended a Gluten-free diet?": "Int8",
    "Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?": "Int8",
    "Does the patient smoke?": "Int8",
    "Was the patient offered an additional appointment with a paediatric dietitian?": "Int8",
    "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?": "Int8",
    "Reason for admission": "Int8",
    "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?": "Int8",
    "Only complete if OTHER selected: Reason for admission (free text)": "str",
}

NONNULL_FIELDS = [
    "NHS Number",
    "Date of Birth",
    "Diabetes Type",
    "PDU Number",
    "Visit/Appointment Date",
]
