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
    },
    "outcomes": {
        "title": "Outcomes",
        "description": "Outcomes are presented below for all children and young people with Type 1 diabetes. HbA1c excludes all measurements taken in the first 90 days after diagnosis.",
    },
    "treatment": {
        "title": "Treatment",
        "description": "Lorem ipsum dolor sit amet consectetur adipisicing elit. Nemo veniam nihil, est adipisci quis optio esse ad neque, eligendi rem omnis earum. Adipisci at veritatis, animi sapiente corrupti commodi dolorum! ",
        "headers": [
            "NHS NUMBER",
            "value",
        ],
    },
}
# TODO: might be nicer to move into above dict
KPI_CATEGORY_ATTR_MAP = {
    "health_checks": list(range(25, 32)),
    "additional_care_processes": list(range(33, 41)),
    "care_at_diagnosis": list(range(41, 44)),
    "outcomes": list(range(44, 47)),
    "treatment": list(range(13, 21)),
}
