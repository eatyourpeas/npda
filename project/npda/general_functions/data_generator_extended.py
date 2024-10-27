from datetime import date, timedelta
from enum import Enum
import random

from django.db import transaction
from project.npda.general_functions.audit_period import (
    get_audit_period_for_date,
    get_quarters_for_audit_period,
)
from project.npda.general_functions.random_date import get_random_date
from project.npda.models.patient import Patient
from project.npda.models.visit import Visit
from project.npda.tests.factories.patient_factory import PatientFactory
from project.npda.tests.factories.visit_factory import VisitFactory

# Importing constants
from project.constants import (
    SEX_TYPE,
    DIABETES_TYPES,
    ETHNICITIES,
    HBA1C_FORMATS,
    GLUCOSE_MONITORING_TYPES,
    TREATMENT_TYPES,
    YES_NO_UNKNOWN,
    RETINAL_SCREENING_RESULTS,
    ALBUMINURIA_STAGES,
    THYROID_TREATMENT_STATUS,
    SMOKING_STATUS,
    HOSPITAL_ADMISSION_REASONS,
    DKA_ADDITIONAL_THERAPIES,
)


class AgeRange(Enum):
    """
    Enum class to represent the range of ages for children.
    """

    AGE_0_4 = (0, 4)
    AGE_5_10 = (5, 10)
    AGE_11_15 = (11, 15)
    AGE_16_19 = (16, 19)
    AGE_20_25 = (20, 25)


class VisitType(Enum):
    """
    Enum class to represent the type of visit for a child.
    """

    CLINIC = "clinic"
    ANNUAL_REVIEW = "annual_review"
    DIETICIAN = "dietician"
    PSYCHOLOGY = "psychology"
    HOSPITAL_ADMISSION = "hospital_admission"


class HbA1cTargetRange(Enum):
    """
    Enum class to represent the level of diabetes control for a child.
    """

    TARGET = "On Target"
    ABOVE = "Above Target"
    WELL_ABOVE = "Well Above Target"


class FakePatientCreator:

    DEFAULT_VISIT_TYPE = [
        VisitType.CLINIC,
        VisitType.CLINIC,
        VisitType.ANNUAL_REVIEW,
        VisitType.DIETICIAN,
    ]

    def __init__(self, audit_start_date: date, audit_end_date: date):
        """Uses audit dates to determine the audit period for the fake patient(s)."""

        self.audit_start_date, self.audit_end_date = (
            audit_start_date,
            audit_end_date,
        )

    def build_fake_patients(
        self,
        n: int,
        age_range: AgeRange,
        **patient_kwargs,
    ) -> list[Patient]:
        """Returns list of `n` fake patients, that are NOT yet stored to db.

        Can additionally pass in any kwargs to the PatientFactory e.g.
        `postcode="123". Values not explicity passed in will be set to defaults
        defined in the PatientFactory.
        """
        new_pts = PatientFactory.build_batch(
            size=n,
            age_range=age_range,
            audit_start_date=self.audit_start_date,
            audit_end_date=self.audit_end_date,
            **patient_kwargs,
        )
        return new_pts

    def build_fake_visits(
        self,
        patients: list[Patient],
        age_range: AgeRange,
        hb1ac_target_range: HbA1cTargetRange = HbA1cTargetRange.TARGET,
        visit_types: list[VisitType] = DEFAULT_VISIT_TYPE,
        **visit_kwargs,
    ) -> list[Visit]:
        """Returns a list of fake Visit objects for the given patients.

        Can additionally pass in any kwargs to the VisitFactory e.g.
        `is_valid=True`.

        Method:
            1) For each patient, assign every visit type in `visit_types`,
                filled with appropriate values relevant to that VisitType.
            2) Visit.visit_dates are spread evenly across the audit period, per
                quarter.

                E.g. if 12 VisitTypes are assigned, 3 will be in each
                quarter.

                Within each quarter, the visit_dates are randomly
                assigned within that quarter's date range.
        """
        visits = []
        # Each patient is assigned n visits, defined by `visit_types`
        for patient in patients:

            # Need to evenly batch inputted visits into 4 buckets, 1 for
            # each quarter
            total_visits = len(visit_types)
            n_visits_per_quarter = total_visits // 4

            # Store visits per quarter, where visits_batched_by_quarter[i]
            # stores the visits in the ith(+1) quarter i.e.
            # visits_batched_by_quarter[2] has Q3 visits
            if total_visits < 4:
                visits_batched_by_quarter = [[v] for v in visit_types]
            else:
                visits_batched_by_quarter = [
                    # q1
                    visit_types[0:n_visits_per_quarter],
                    # q2
                    visit_types[
                        n_visits_per_quarter : n_visits_per_quarter * 2
                    ],
                    # q3
                    visit_types[
                        n_visits_per_quarter * 2 : n_visits_per_quarter * 3
                    ],
                    # q4 - all remaining
                    visit_types[n_visits_per_quarter * 3 :],
                ]

            # Get dates for quarters
            audit_quarters = get_quarters_for_audit_period(
                self.audit_start_date, self.audit_end_date
            )

            for q, visits_in_q in enumerate(visits_batched_by_quarter):

                # For this quarter, get date bounds
                quarter_start_date, quarter_end_date = audit_quarters[q]

                # For each visit, randomly assign a date within quarter
                for visit_type in visits_in_q:
                    visit_date = get_random_date(
                        quarter_start_date, quarter_end_date
                    )

                    # Get the correct kwarg measurements for the visit type
                    # These will be fed into this VisitFactory's.build() call
                    measurements = self.get_measures_for_visit_type(
                        visit_type=visit_type,
                        age_range=age_range,
                        visit_date=visit_date,
                        diabetes_type=patient.diabetes_type,
                        hba1_target_range=hb1ac_target_range,
                    )

                    # Build the Visit instance
                    visit = VisitFactory.build(
                        patient=patient,
                        visit_date=visit_date,
                        **measurements,
                        **visit_kwargs,
                    )
                    visits.append(visit)
        return visits

    def create_and_save_fake_patients(
        self,
        n: int,
        age_range: AgeRange,
        hb1ac_target_range: HbA1cTargetRange = HbA1cTargetRange.TARGET,
        visit_types: list[VisitType] = DEFAULT_VISIT_TYPE,
        **patient_kwargs,
    ):
        """Creates and saves `n` fake patients, with the given `age_range` to
        the db.

        Each Patient created will have associated Visits, randomly allocated
        throughout each quarter of the audit period.

        * `visit_types` -> A list of VisitTypes to create for each patient.
            [
                VisitType.CLINIC,
                VisitType.ANNUAL_REVIEW,
                VisitType.DIETICIAN,
                VisitType.DIETICIAN,
                ...
            ]

        Will sequentially go through list creating visit
        type according to those characteristics.

        *patient_kwargs -> Any additional kwargs to pass to the PatientFactory
        """

        # Use a transaction to speed up bulk insertions
        with transaction.atomic():
            # Step 1: Create `n` patients in batch
            # Need to ensure we use the .create method so related factories
            # Transfer and PDU are made.
            patients = PatientFactory.create_batch(
                size=n,
                age_range=age_range,
                # We're going to manually create visits for each patient
                visit=None,
                **patient_kwargs,
            )

            # Step 2: Build visits
            visits = self.build_fake_visits(
                patients=patients,
                age_range=age_range,
                hb1ac_target_range=hb1ac_target_range,
                visit_types=visit_types,
            )

            # Step 3: Bulk create all visits at once
            Visit.objects.bulk_create(visits)

        self.saved_patients = patients
        self.saved_visits = visits
        return patients

    def get_measures_for_visit_type(
        self,
        visit_type: VisitType,
        age_range: AgeRange,
        visit_date: date,
        diabetes_type: int,
        hba1_target_range: int,
    ):
        """Returns a dictionary of measures for a given visit type."""
        visit_measure_map = {
            VisitType.CLINIC: self._clinic_measures(
                age_range=age_range,
                visit_date=visit_date,
                diabetes_type=diabetes_type,
                hba1_target_range=hba1_target_range,
            ),
            VisitType.ANNUAL_REVIEW: self._annual_review_measures(
                visit_date=visit_date,
            ),
            VisitType.DIETICIAN: self._dietician_observations(
                visit_date=visit_date,
            ),
            VisitType.PSYCHOLOGY: self._psychological_observations(
                visit_date=visit_date,
            ),
            VisitType.HOSPITAL_ADMISSION: self._hospital_admission_observations(
                visit_date=visit_date,
            ),
        }
        return visit_measure_map[visit_type]

    def _clinic_measures(
        self,
        age_range: AgeRange,
        visit_date: date,
        diabetes_type: int,
        hba1_target_range: int,
    ):
        """
        Gather all the measures for a clinic visit. These include
        - height
        - weight
        - HbA1c
        - treatment
        - CGM
        - BP
        """
        height, weight, height_weight_observation_date = (
            self._height_weight_observations(
                age_range=age_range, visit_date=visit_date
            )
        )

        hba1c, hba1c_format, hba1c_date = self._hba1c_observations(
            hba1_target_range=hba1_target_range,
            visit_date=visit_date,
        )

        glucose_monitoring = self._continuous_glucose_monitoring_observations()

        treatment, closed_loop_system = self._treatment_observations(
            diabetes_type=diabetes_type
        )

        (
            diastolic_blood_pressure,
            systolic_blood_pressure,
            blood_pressure_observation_date,
        ) = self._bp_observations(age_range=age_range, visit_date=visit_date)

        return {
            "height": height,
            "weight": weight,
            "height_weight_observation_date": height_weight_observation_date,
            "hba1c": hba1c,
            "hba1c_format": hba1c_format,
            "hba1c_date": hba1c_date,
            "glucose_monitoring": glucose_monitoring,
            "treatment": treatment,
            "closed_loop_system": closed_loop_system,
            "diastolic_blood_pressure": diastolic_blood_pressure,
            "systolic_blood_pressure": systolic_blood_pressure,
            "blood_pressure_observation_date": blood_pressure_observation_date,
        }

    def _annual_review_measures(self, visit_date: date):
        """
        Gather all the measures for an annual review visit.
        These dictate the measures that are taken for an annual review visit:
            - "foot_examination_observation_date"
            - "retinal_screening_result"
            - "retinal_screening_observation_date"
            - "albumin_creatinine_ratio"
            - "albumin_creatinine_ratio_date"
            - "albuminuria_stage"
            - "total_cholesterol"
            - "total_cholesterol_date"
            - "thyroid_function_date"
            - "thyroid_treatment_status"
            - "coeliac_screen_date"
            - "gluten_free_diet"
            - "smoking_status"
            - "smoking_cessation_referral_date"
            - "carbohydrate_counting_level_three_education_date"
            - "flu_immunisation_recommended_date"
            - "ketone_meter_training"
            - "sick_day_rules_training_date"

        """
        foot_examination_observation_date = self._foot_observations(
            visit_date=visit_date
        )
        retinal_screening_result, retinal_screening_observation_date = (
            self._decs_observations(visit_date=visit_date)
        )
        (
            albumin_creatinine_ratio,
            albumin_creatinine_ratio_date,
            albuminuria_stage,
        ) = self._acr_observations(visit_date=visit_date)
        total_cholesterol, total_cholesterol_date = (
            self._cholesterol_observations(visit_date=visit_date)
        )
        thyroid_function_date, thyroid_treatment_status = (
            self._thyroid_observations(visit_date=visit_date)
        )
        coeliac_screen_date, gluten_free_diet = self._coeliac_observations(
            visit_date=visit_date
        )
        smoking_status, smoking_cessation_referral_date = (
            self._smoking_observations(visit_date=visit_date)
        )
        carbohydrate_counting_level_three_education_date = (
            self._carbohydrate_counting_observations(visit_date=visit_date)
        )
        flu_immunisation_recommended_date = (
            self._flu_immunisation_observations(visit_date=visit_date)
        )
        ketone_meter_training = self._ketone_meter_observations()
        sick_day_rules_training_date = self._sick_day_rules_observations(
            visit_date=visit_date
        )

        return {
            "foot_examination_observation_date": foot_examination_observation_date,
            "retinal_screening_result": retinal_screening_result,
            "retinal_screening_observation_date": retinal_screening_observation_date,
            "albumin_creatinine_ratio": albumin_creatinine_ratio,
            "albumin_creatinine_ratio_date": albumin_creatinine_ratio_date,
            "albuminuria_stage": albuminuria_stage,
            "total_cholesterol": total_cholesterol,
            "total_cholesterol_date": total_cholesterol_date,
            "thyroid_function_date": thyroid_function_date,
            "thyroid_treatment_status": thyroid_treatment_status,
            "coeliac_screen_date": coeliac_screen_date,
            "gluten_free_diet": gluten_free_diet,
            "smoking_status": smoking_status,
            "smoking_cessation_referral_date": smoking_cessation_referral_date,
            "carbohydrate_counting_level_three_education_date": carbohydrate_counting_level_three_education_date,
            "flu_immunisation_recommended_date": flu_immunisation_recommended_date,
            "ketone_meter_training": ketone_meter_training,
            "sick_day_rules_training_date": sick_day_rules_training_date,
        }

    def _dietician_observations(self, visit_date: date):
        """
        Generates random dietician observations for a child.
        Allocate the visit date to the date of the observation.

        Returns dict of:
            dietician_additional_appointment_offered: int
            dietician_additional_appointment_date: date
        """
        dietician_additional_appointment_offered = random.choice(
            YES_NO_UNKNOWN
        )[0]
        dietician_additional_appointment_date = visit_date
        return {
            "dietician_additional_appointment_offered": dietician_additional_appointment_offered,
            "dietician_additional_appointment_date": dietician_additional_appointment_date,
        }

    def _psychological_observations(self, visit_date: date):
        """
        Generates random psychological screening observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            psychological_screening_assessment_date: date
            psychological_additional_support_status: int
        """
        psychological_screening_assessment_date = visit_date
        psychological_additional_support_status = random.choice(
            YES_NO_UNKNOWN
        )[0]
        return {
            "psychological_screening_assessment_date": psychological_screening_assessment_date,
            "psychological_additional_support_status": psychological_additional_support_status,
        }

    def _hospital_admission_observations(
        self,
        visit_date: date,
    ):
        """
        Generates random hospital admission observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
        """
        hospital_admission_date = visit_date
        hospital_discharge_date = visit_date
        hospital_admission_reason = random.choice(HOSPITAL_ADMISSION_REASONS)[
            0
        ]
        dka_additional_therapies = random.choice(DKA_ADDITIONAL_THERAPIES)[0]
        hospital_admission_other = None
        return {
            "hospital_admission_date": hospital_admission_date,
            "hospital_discharge_date": hospital_discharge_date,
            "hospital_admission_reason": hospital_admission_reason,
            "dka_additional_therapies": dka_additional_therapies,
            "hospital_admission_other": hospital_admission_other,
        }

    def _height_weight_observations(
        self,
        age_range: AgeRange,
        visit_date: date,
    ):
        """
        Generates random height and weight observations for a child.
        Use the age_range to determine the range of values for height and weight.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            height: float
            weight: float
            height_weight_observation_date: date
        """
        height_weight_observations = {
            AgeRange.AGE_0_4: (50, 110, 10, 20),
            AgeRange.AGE_5_10: (110, 150, 20, 40),
            AgeRange.AGE_11_15: (150, 170, 40, 70),
            AgeRange.AGE_16_19: (170, 190, 60, 90),
            AgeRange.AGE_20_25: (170, 190, 60, 90),
        }

        height_min, height_max, weight_min, weight_max = (
            height_weight_observations.get(AgeRange(age_range.value))
        )

        height = round(random.uniform(height_min, height_max), 2)
        weight = round(random.uniform(weight_min, weight_max), 2)
        height_weight_observation_date = (
            visit_date  # set the date of the observation to the visit date
        )
        return height, weight, height_weight_observation_date

    def _hba1c_observations(
        self,
        hba1_target_range: HbA1cTargetRange,
        visit_date: date,
    ):
        """
        Generates random HbA1c observations for a child.
        Use the diabetes type to determine the range of values for HbA1c in mmol/mol.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            hba1c: int
            hba1c_format: int
            hba1c_date: date
        """
        hba1c_observations = {
            HbA1cTargetRange.TARGET: (48, 58),
            HbA1cTargetRange.ABOVE: (58, 85),
            HbA1cTargetRange.WELL_ABOVE: (85, 120),
        }

        hba1c_min, hba1c_max = hba1c_observations.get(
            HbA1cTargetRange(hba1_target_range.value)
        )
        hba1c = random.randint(hba1c_min, hba1c_max)
        hba1c_format = HBA1C_FORMATS[0][0]  # mmol/mol
        hba1c_date = visit_date
        return hba1c, hba1c_format, hba1c_date

    def _continuous_glucose_monitoring_observations(
        self,
    ):
        """
        Generates random continuous glucose monitoring observations for a child.
        Allocate the visit date to the date of the observation.

        Returns:
            glucose_monitoring: int
        """
        glucose_monitoring = random.choice(GLUCOSE_MONITORING_TYPES)[0]
        return glucose_monitoring

    def _treatment_observations(self, diabetes_type: int):
        """
        Generates random treatment observations for a child.
        Use the diabetes type to determine the range of values for treatment.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            treatment: int
            closed_loop_system:
        """
        if diabetes_type == 1:
            treatment = random.choice(TREATMENT_TYPES[0:6])[
                0
            ]  # MDI or pump options
        else:
            treatment = random.choice(
                [1, 2, 4, 5, 7, 8, 9]
            )  # insulin or non-insulin options compatible with type 2 diabetes

        if diabetes_type == 1:
            closed_loop_system = random.choice([True, False])
        else:
            closed_loop_system = YES_NO_UNKNOWN[0][0]  # No

        return treatment, closed_loop_system

    def _bp_observations(
        self,
        age_range: AgeRange,
        visit_date: date,
    ):
        """
        Generates random blood pressure observations for a child based on the age range.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            diastolic_blood_pressure: int
            systolic_blood_pressure: int
            blood_pressure_observation_date: date
        """
        bp_ranges = {
            AgeRange.AGE_0_4: (40, 50, 80, 90),
            AgeRange.AGE_5_10: (40, 50, 90, 100),
            AgeRange.AGE_11_15: (50, 60, 95, 105),
            AgeRange.AGE_16_19: (60, 70, 110, 130),
            AgeRange.AGE_20_25: (60, 70, 110, 130),
        }
        selected_bp_range = bp_ranges.get(AgeRange(age_range.value))

        diastolic_blood_pressure = random.randint(
            selected_bp_range[0], selected_bp_range[1]
        )
        systolic_blood_pressure = random.randint(
            selected_bp_range[2], selected_bp_range[3]
        )
        blood_pressure_observation_date = visit_date
        return (
            diastolic_blood_pressure,
            systolic_blood_pressure,
            blood_pressure_observation_date,
        )

    def _foot_observations(self, visit_date: date):
        """
        Generates random foot examination observations for a child.
        Allocate the visit date to the date of the observation.

        Returns:
            foot_examination_observation_date: date
        """
        foot_examination_observation_date = visit_date
        return foot_examination_observation_date

    def _decs_observations(self, visit_date: date):
        """
        Generates random DECS observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            retinal_screening_result: int
            retinal_screening_observation_date: date
        """
        retinal_screening_observation_date = visit_date
        retinal_screening_result = random.choice(RETINAL_SCREENING_RESULTS)[0]
        return retinal_screening_result, retinal_screening_observation_date

    def _acr_observations(self, visit_date: date):
        """
        Generates random ACR observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            albumin_creatinine_ratio: int
            albumin_creatinine_ratio_date: date
            albuminuria_stage: int
        """
        albumin_creatinine_ratio = random.randint(0, 300)
        albumin_creatinine_ratio_date = visit_date
        albuminuria_stage = random.choice(ALBUMINURIA_STAGES)[0]
        return (
            albumin_creatinine_ratio,
            albumin_creatinine_ratio_date,
            albuminuria_stage,
        )

    def _cholesterol_observations(self, visit_date: date):
        """
        Generates random cholesterol observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            total_cholesterol: float
            total_cholesterol_date: date
        """
        total_cholesterol = round(random.uniform(2, 7), 2)
        total_cholesterol_date = visit_date
        return total_cholesterol, total_cholesterol_date

    def _thyroid_observations(self, visit_date: date):
        """
        Generates random thyroid function observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            thyroid_function_date: date
            thyroid_treatment_status: int
        """
        thyroid_function_date = visit_date
        thyroid_treatment_status = random.choice(THYROID_TREATMENT_STATUS)[0]
        return thyroid_function_date, thyroid_treatment_status

    def _coeliac_observations(self, visit_date: date):
        """
        Generates random coeliac screening observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            coeliac_screen_date: date
            gluten_free_diet: int
        """
        coeliac_screen_date = visit_date
        gluten_free_diet = random.choice(YES_NO_UNKNOWN)[0]
        return coeliac_screen_date, gluten_free_diet

    def _smoking_observations(self, visit_date: date):
        """
        Generates random smoking status observations for a child.
        Allocate the visit date to the date of the observation.

        Returns tuple of:
            smoking_status: int
            smoking_cessation_referral_date: date
        """
        smoking_status = random.choice(SMOKING_STATUS)[0]
        smoking_cessation_referral_date = visit_date
        return smoking_status, smoking_cessation_referral_date

    def _carbohydrate_counting_observations(self, visit_date: date):
        """
        Generates random carbohydrate counting observations for a child.
        Allocate the visit date to the date of the observation.

        Returns:
            carbohydrate_counting_level_three_education_date: date
        """
        carbohydrate_counting_level_three_education_date = visit_date
        return carbohydrate_counting_level_three_education_date

    def _flu_immunisation_observations(self, visit_date: date):
        """
        Generates random flu immunisation observations for a child.
        Allocate the visit date to the date of the observation.

        Returns:
            flu_immunisation_recommended_date: date
        """
        flu_immunisation_recommended_date = visit_date
        return flu_immunisation_recommended_date

    def _ketone_meter_observations(self):
        """
        Generates random ketone meter observations for a child.

        Returns ketone_meter_training: int
        """
        ketone_meter_training = random.choice(YES_NO_UNKNOWN)[0]
        return ketone_meter_training

    def _sick_day_rules_observations(self, visit_date: date):
        """
        Generates random sick day rules observations for a child.
        Allocate the visit date to the date of the observation.

        Returns:
            sick_day_rules_training_date: date
        """
        sick_day_rules_training_date = visit_date
        return sick_day_rules_training_date
