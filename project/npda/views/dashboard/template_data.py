"""Contains the data for the dashboard template."""

TEXT = {
    "health_checks": {
        "title": "Seven Key Care Processes",
        "description": "HbA1c, BMI, and thyroid screen must be completed annually for all children and young people with Type 1 diabetes. Urinary albumin, blood pressure, and foot exam are mandatory for young people aged 12 and above. Eye screening is mandatory every 2 years for young people aged 12 and above, unless retinopathy was observed at a previous screen.",
        "headers": [
            "NHS NUMBER",
            ">= 12YO",
            "HBA1C",
            "BMI",
            "THYROID SCREEN",
            "BLOOD PRESSURE",
            "URINARY ALBUMIN",
            "EYE SCREEN",
            "FOOT EXAM",
            "TOTAL",
        ],
        "ineligible_hover_reason": {
            "kpi_25_hba1c": "Does not fulfil criteria for KPI 5",
            "kpi_26_bmi": "Does not fulfil criteria for KPI 5 ",
            "kpi_27_thyroid_screen": "Does not fulfil criteria for KPI 5",
            "kpi_28_blood_pressure": "Does not fulfil criteria for KPI 6",
            "kpi_29_urinary_albumin": "Does not fulfil criteria for KPI 6",
            "kpi_30_retinal_screening": "Does not fulfil criteria for KPI 6",
            "kpi_31_foot_examination": "Does not fulfil criteria for KPI 6",
        },
    },
    "additional_care_processes": {
        "title": "Additional Care Proccesses",
        "description": "These additional care processes are recommended by NICE for children and young people with Type 1 diabetes of all ages (and ineligible otherwise), with the exception of smoking status and referral to smoking cessation services, which apply to young people aged 12 and above.",
        "headers": [
            "NHS NUMBER",
            "HBA1C 4+",
            "Psychological assessment",
            "Smoking status screened",
            "Referral to smoking cessation service",
            "Additional dietetic appointment offered",
            "Patients attending additional dietetic appointment",
            "Influenza immunisation recommended",
            "Sick day rules advice",
        ],
        "ineligible_hover_reason": {
            "kpi_33_hba1c_4plus": "Does not fulfil criteria for KPI 5",
            "kpi_34_psychological_assessment": "Does not fulfil criteria for KPI 5",
            "kpi_35_smoking_status_screened": "Does not fulfil criteria for KPI 6",
            "kpi_36_referral_to_smoking_cessation_service": "Does not fulfil criteria for KPI 6",
            "kpi_37_additional_dietetic_appointment_offered": "Does not fulfil criteria for KPI 5",
            "kpi_38_patients_attending_additional_dietetic_appointment": "Does not fulfil criteria for KPI 5",
            "kpi_39_influenza_immunisation_recommended": "Does not fulfil criteria for KPI 5",
            "kpi_40_sick_day_rules_advice": "Does not fulfil criteria for KPI 1",
        },
    },
    "care_at_diagnosis": {
        "title": "Care at Diagnosis",
        "description": "Children and young people with Type 1 diabetes should be screened for thyroid disease and coeliac disease within 90 days of diagnosis. Newly diagnosed children and young people should also receive level 3 carbohydrate counting education within 14 days of diagnosis.",
        "headers": [
            "NHS NUMBER",
            "COELIAC DISEASE SCREENING",
            "THYROID DISEASE SCREENING",
            "CARBOHYDRATE COUNTING EDUCATION",
        ],
        "ineligible_hover_reason": {
            "kpi_41_coeliac_disease_screening": "Does not fulfil criteria for KPI 7, diagnosed at least 90 days before the end of the audit period",
            "kpi_42_thyroid_disease_screening": "Does not fulfil criteria for KPI 7, diagnosed at least 90 days before the end of the audit period",
            "kpi_43_carbohydrate_counting_education": "Does not fulfil criteria for KPI 7, diagnosed at least 90 days before the end of the audit period",
        },
    },
    "outcomes": {
        "title": "Outcomes",
        "description": "Outcomes are presented below for all children and young people with Type 1 diabetes. HbA1c excludes all measurements taken in the first 90 days after diagnosis.",
        "headers": [
            "NHS NUMBER",
            "Mean HbA1c",
            "Median HbA1c",
            "Number of Admissions",
            "Number of DKA Admissions",
            "Required additional psych support",
            "Albuminuria present",
        ],
        "ineligible_hover_reason": {
            
        },
    },
    "treatment": {
        "title": "Treatment",
        "description": "Treatment regimens are presented below for all children and young people included within the audit.",
        "headers": [
            "NHS NUMBER",
            "Treatment Regimen",
            "Continuous Glucose Monitoring",
            "Hybrid Closed Loop",
        ],
        "ineligible_hover_reason": {
            
        },
    },
}
# TODO: might be nicer to move into above dict
KPI_CATEGORY_ATTR_MAP = {
    "health_checks": list(range(25, 32)),
    "additional_care_processes": list(range(33, 41)),
    "care_at_diagnosis": list(range(41, 44)),
    "outcomes": list(range(44, 50)),
    "treatment": list(range(13, 25)),
}
