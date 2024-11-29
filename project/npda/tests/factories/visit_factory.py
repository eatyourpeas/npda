"""Factory fn to create new Visit, related to a Patient.
"""

# standard imports
from datetime import timedelta

# third-party imports
import factory

# rcpch imports
from project.npda.models import Visit
from project.constants.visit_categories import VISIT_FIELDS

COMPLETED_VISIT = {
    "height": 123,
    "weight": 35,
    "height_weight_observation_date": "2021-01-01",
    "hba1c": 12.3,
    "hba1c_format": 1,
    "hba1c_date": "2021-01-01",
    "treatment": 2,
    "closed_loop_system": 1,
    "glucose_monitoring": 3,
    "systolic_blood_pressure": 100,
    "diastolic_blood_pressure": 25,
    "blood_pressure_observation_date": "2021-01-01",
    "foot_examination_observation_date": "2021-01-01",
    "retinal_screening_observation_date": "2021-01-01",
    "retinal_screening_result": 1,
    "albumin_creatinine_ratio": 1.2,
    "albumin_creatinine_ratio_date": "2021-01-01",
    "albuminuria_stage": 1,
    "total_cholesterol_date": "2021-01-01",
    "thyroid_function_date": "2021-01-01",
    "thyroid_treatment_status": 1,
    "coeliac_screen_date": "2021-01-01",
    "gluten_free_diet": 1,
    "psychological_screening_assessment_date": "2021-01-01",
    "psychological_additional_support_status": 1,
    "smoking_status": 1,
    "smoking_cessation_referral_date": 1,
    "carbohydrate_counting_level_three_education_date": "2021-01-01",
    "dietician_additional_appointment_offered": 1,
    "dietician_additional_appointment_date": "2021-01-01",
    "ketone_meter_training": 1,
    "flu_immunisation_recommended_date": "2021-01-01",
    "hospital_admission_date": "2021-01-01",
    "hospital_discharge_date": "2021-01-01",
    "hospital_admission_reason": 1,
    "dka_additional_therapies": 1,
    "hospital_admission_other": "other",
}


class VisitFactory(factory.django.DjangoModelFactory):
    """Dependency factory for creating a minimum viable NPDAManagement.

    This Factory is generated AFTER a Patient has been generated.
    """

    class Meta:
        model = Visit

    # Once Patient instance made, it will attach to this instance
    patient = None
