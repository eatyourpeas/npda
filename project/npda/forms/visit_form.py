from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.core.exceptions import ValidationError
from ...constants.styles import *
from ...constants import *
from ..general_functions.validate_dates import validate_date
from ..forms.external_visit_validators import validate_visit_sync
from ..models import Visit


class DateInput(forms.DateInput):
    input_type = "date"


class VisitForm(forms.ModelForm):

    patient = None

    class Meta:
        model = Visit
        fields = [
            "visit_date",
            "height",
            "weight",
            "bmi",
            "height_weight_observation_date",
            "hba1c",
            "hba1c_format",
            "hba1c_date",
            "treatment",
            "closed_loop_system",
            "glucose_monitoring",
            "systolic_blood_pressure",
            "diastolic_blood_pressure",
            "blood_pressure_observation_date",
            "foot_examination_observation_date",
            "retinal_screening_observation_date",
            "retinal_screening_result",
            "albumin_creatinine_ratio",
            "albumin_creatinine_ratio_date",
            "albuminuria_stage",
            "total_cholesterol",
            "total_cholesterol_date",
            "thyroid_function_date",
            "thyroid_treatment_status",
            "coeliac_screen_date",
            "gluten_free_diet",
            "psychological_screening_assessment_date",
            "psychological_additional_support_status",
            "smoking_status",
            "smoking_cessation_referral_date",
            "carbohydrate_counting_level_three_education_date",
            "dietician_additional_appointment_offered",
            "dietician_additional_appointment_date",
            "flu_immunisation_recommended_date",
            "ketone_meter_training",
            "sick_day_rules_training_date",
            "hospital_admission_date",
            "hospital_discharge_date",
            "hospital_admission_reason",
            "dka_additional_therapies",
            "hospital_admission_other",
        ]

        widgets = {
            "visit_date": DateInput(),
            "height": forms.TextInput(),
            "weight": forms.TextInput(),
            "bmi": forms.TextInput(attrs={"required": "false"}),
            "height_weight_observation_date": DateInput(),
            "hba1c": forms.TextInput(),
            "hba1c_format": forms.Select(),
            "hba1c_date": DateInput(),
            "treatment": forms.Select(),
            "closed_loop_system": forms.Select(),
            "glucose_monitoring": forms.Select(),
            "systolic_blood_pressure": forms.TextInput(),
            "diastolic_blood_pressure": forms.TextInput(),
            "blood_pressure_observation_date": DateInput(),
            "foot_examination_observation_date": DateInput(),
            "retinal_screening_observation_date": DateInput(),
            "retinal_screening_result": forms.Select(),
            "albumin_creatinine_ratio": forms.TextInput(),
            "albumin_creatinine_ratio_date": DateInput(),
            "albuminuria_stage": forms.Select(),
            "total_cholesterol": forms.TextInput(),
            "total_cholesterol_date": DateInput(),
            "thyroid_function_date": DateInput(),
            "thyroid_treatment_status": forms.Select(),
            "coeliac_screen_date": DateInput(),
            "gluten_free_diet": forms.Select(),
            "psychological_screening_assessment_date": DateInput(),
            "psychological_additional_support_status": forms.Select(),
            "smoking_status": forms.Select(),
            "smoking_cessation_referral_date": DateInput(),
            "carbohydrate_counting_level_three_education_date": DateInput(),
            "dietician_additional_appointment_offered": forms.Select(),
            "dietician_additional_appointment_date": DateInput(),
            "flu_immunisation_recommended_date": DateInput(),
            "ketone_meter_training": forms.Select(),
            "sick_day_rules_training_date": DateInput(),
            "hospital_admission_date": DateInput(),
            "hospital_discharge_date": DateInput(),
            "hospital_admission_reason": forms.Select(),
            "dka_additional_therapies": forms.Select(),
            "hospital_admission_other": forms.TextInput(),
        }

    categories = [
        "Measurements",
        "HBA1c",
        "Treatment",
        "CGM",
        "BP",
        "Foot Care",
        "DECS",
        "ACR",
        "Cholesterol",
        "Thyroid",
        "Coeliac",
        "Psychology",
        "Smoking",
        "Dietician",
        "Sick Day Rules",
        "Immunisation (flu)",
        "Hospital Admission",
    ]

    def __init__(self, *args, **kwargs):
        self.patient = kwargs["initial"].get("patient")
        super(VisitForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            model_field = Visit._meta.get_field(field_name)

            if hasattr(model_field, "category"):
                field.category = model_field.category

    """
    Custom clean method for all fields requiring choices
    """

    def clean_smoking_status(self):
        data = self.cleaned_data["smoking_status"]
        # Convert the list of tuples to a dictionary
        smoking_status_dict = dict(SMOKING_STATUS)

        if data is None or data in smoking_status_dict:
            return data
        else:
            options = str(SMOKING_STATUS).strip("[]").replace(")", "").replace("(", "")
            raise ValidationError(
                f"'{data}' is not a value for 'Smoking Status'. Please select one of {options}."
            )

    def clean_thyroid_treatment_status(self):
        data = self.cleaned_data["thyroid_treatment_status"]
        # Convert the list of tuples to a dictionary
        thyroid_treatment_dict = dict(THYROID_TREATMENT_STATUS)

        if data is None or data in thyroid_treatment_dict:
            return data
        else:
            options = (
                str(THYROID_TREATMENT_STATUS)
                .strip("[]")
                .replace(")", "")
                .replace("(", "")
            )
            raise ValidationError(
                f"'{data}' is not a value for 'Thyroid Treatment Status'. Please select one of {options}."
            )

    def clean_closed_loop_system(self):
        data = self.cleaned_data["closed_loop_system"]
        # Convert the list of tuples to a dictionary
        closed_loop_system_dict = dict(CLOSED_LOOP_TYPES)

        if data is None or data in closed_loop_system_dict:
            return data
        else:
            options = (
                str(CLOSED_LOOP_TYPES).strip("[]").replace(")", "").replace("(", "")
            )
            raise ValidationError(
                f"'{data}' is not a value for 'Closed Loop System'. Please select one of {options}."
            )

    def clean_hospital_admission_reason(self):
        data = self.cleaned_data["hospital_admission_reason"]
        # Convert the list of tuples to a dictionary
        hospital_admission_reason_dict = dict(HOSPITAL_ADMISSION_REASONS)

        if data is None or data in hospital_admission_reason_dict:
            return data
        else:
            options = (
                str(HOSPITAL_ADMISSION_REASONS)
                .strip("[]")
                .replace(")", "")
                .replace("(", "")
            )
            raise ValidationError(
                f"'{data}' is not a value for 'Hospital Admission Reason'. Please select one of {options}."
            )

    def clean_albuminuria_stage(self):
        data = self.cleaned_data["albuminuria_stage"]
        # Convert the list of tuples to a dictionary
        albuminuria_stage_dict = dict(ALBUMINURIA_STAGES)

        if data is None or data in albuminuria_stage_dict:
            return data
        else:
            options = (
                str(ALBUMINURIA_STAGES).strip("[]").replace(")", "").replace("(", "")
            )
            raise ValidationError(
                f"'{data}' is not a value for 'Albuminuria Stage'. Please select one of {options}."
            )

    def clean_psychological_additional_support_status(self):
        data = self.cleaned_data["psychological_additional_support_status"]
        # Convert the list of tuples to a dictionary
        psychological_additional_support_status_dict = dict(YES_NO_UNKNOWN)

        if data is None or data in psychological_additional_support_status_dict:
            return data
        else:
            options = str(YES_NO_UNKNOWN).strip("[]").replace(")", "").replace("(", "")
            raise ValidationError(
                f"'{data}' is not a value for 'Psychological Additional Support Status'. Please select one of {options}."
            )

    def clean_dietian_additional_appointment_offered(self):
        data = self.cleaned_data["dietician_additional_appointment_offered"]
        # Convert the list of tuples to a dictionary
        dietitian_additional_appointment_offered_dict = dict(YES_NO_UNKNOWN)

        if data is None or data in dietitian_additional_appointment_offered_dict:
            return data
        else:
            options = str(YES_NO_UNKNOWN).strip("[]").replace(")", "").replace("(", "")
            raise ValidationError(
                f"'{data}' is not a value for 'Dietician Additional Appointment Offered'. Please select one of {options}."
            )

    def clean_ketone_meter_training(self):
        data = self.cleaned_data["ketone_meter_training"]
        # Convert the list of tuples to a dictionary
        ketone_meter_training_dict = dict(YES_NO_UNKNOWN)

        if data is None or data in ketone_meter_training_dict:
            return data
        else:
            options = str(YES_NO_UNKNOWN).strip("[]").replace(")", "").replace("(", "")
            raise ValidationError(
                f"'{data}' is not a value for 'Ketone Meter Training'. Please select one of {options}."
            )

    def clean_dka_additional_therapies(self):
        data = self.cleaned_data["dka_additional_therapies"]
        # Convert the list of tuples to a dictionary
        dka_additional_therapies_dict = dict(DKA_ADDITIONAL_THERAPIES)

        if data is None or data in dka_additional_therapies_dict:
            return data
        else:
            options = (
                str(DKA_ADDITIONAL_THERAPIES)
                .strip("[]")
                .replace(")", "")
                .replace("(", "")
            )
            raise ValidationError(
                f"'{data}' is not a value for 'DKA Additional Therapies'. Please select one of {options}."
            )

    def clean_gluten_free_diet(self):
        data = self.cleaned_data["gluten_free_diet"]
        # Convert the list of tuples to a dictionary
        gluten_free_diet_dict = dict(YES_NO_UNKNOWN)

        if data is None or data in gluten_free_diet_dict:
            return data
        else:
            options = str(YES_NO_UNKNOWN).strip("[]").replace(")", "").replace("(", "")
            raise ValidationError(
                "gluten_free_diet",
                [
                    f"'{data}' is not a value for 'Gluten Free Diet'. Please select one of {options}."
                ],
            )

    def clean_hba1c_format(self):
        data = self.cleaned_data["hba1c_format"]
        # Convert the list of tuples to a dictionary
        hba1c_format_dict = dict(HBA1C_FORMATS)

        if data is None or data in hba1c_format_dict:
            return data
        else:
            options = str(HBA1C_FORMATS).strip("[]").replace(")", "").replace("(", "")
            raise ValidationError(
                f"'{data}' is not a value for 'Hba1c Format'. Please select one of {options}."
            )

    def clean_retinal_screening_result(self):
        data = self.cleaned_data["retinal_screening_result"]
        # Convert the list of tuples to a dictionary
        retinal_screening_result_dict = dict(RETINAL_SCREENING_RESULTS)

        if data is None or data in retinal_screening_result_dict:
            return data
        else:
            options = (
                str(RETINAL_SCREENING_RESULTS)
                .strip("[]")
                .replace(")", "")
                .replace("(", "")
            )
            raise ValidationError(
                f"'{data}' is not a value for 'Retinal Screening Result'. Please select one of {options}."
            )

    def clean_treatment(self):
        data = self.cleaned_data["treatment"]
        # Convert the list of tuples to a dictionary
        treatment_dict = dict(TREATMENT_TYPES)

        if data is None or data in treatment_dict:
            return data
        else:
            options = str(TREATMENT_TYPES).strip("[]").replace(")", "").replace("(", "")
            raise ValidationError(
                f"'{data}' is not a value for 'Treatment'. Please select one of {options}."
            )

    def clean_glucose_monitoring(self):
        data = self.cleaned_data["glucose_monitoring"]
        # Convert the list of tuples to a dictionary
        glucose_monitoring_dict = dict(GLUCOSE_MONITORING_TYPES)

        if data is None or data in glucose_monitoring_dict:
            return data
        else:
            options = (
                str(GLUCOSE_MONITORING_TYPES)
                .strip("[]")
                .replace(")", "")
                .replace("(", "")
            )
            raise ValidationError(
                f"'{data}' is not a value for 'Glucose Monitoring'. Please select one of {options}."
            )

    """
    Custom clean methods for all fields requiring numbers
    """

    def clean_height(self):
        # Get the height value, if present round it to 1 decimal place
        data = self.cleaned_data["height"]
        if data is not None:
            if data < 40:
                raise ValidationError(
                    "Please enter a valid height. Cannot be less than 40cm"
                )
            if data > 240:
                raise ValidationError(
                    "Please enter a valid height. Cannot be greater than 240cm"
                )
            data = round(data, 1)
        return data

    def clean_weight(self):
        # Get the weight value, if present round it to 1 decimal place
        data = self.cleaned_data["weight"]
        if data is not None:
            if data < 1:
                raise ValidationError(
                    "Patient Weight (kg)' invalid. Cannot be below 1kg"
                )
            if data > 200:
                raise ValidationError(
                    "Patient Weight (kg)' invalid. Cannot be above 200kg"
                )
            data = round(data, 1)
        return data

    def clean_systolic_blood_pressure(self):
        systolic_blood_pressure = self.cleaned_data["systolic_blood_pressure"]

        if systolic_blood_pressure:
            if systolic_blood_pressure < 80:
                raise ValidationError(
                    "Systolic Blood Pressure out of range. Cannot be below 80"
                )
            elif systolic_blood_pressure > 240:
                raise ValidationError(
                    "Systolic Blood Pressure out of range. Cannot be above 240"
                )

        return systolic_blood_pressure

    def clean_diastolic_blood_pressure(self):
        diastolic_blood_pressure = self.cleaned_data["diastolic_blood_pressure"]

        if diastolic_blood_pressure:
            if diastolic_blood_pressure < 20:
                raise ValidationError(
                    "Diastolic Blood pressure out of range. Cannot be below 20"
                )
            elif diastolic_blood_pressure > 120:
                raise ValidationError(
                    "Diastolic Blood pressure out of range. Cannot be above 120"
                )

        return diastolic_blood_pressure

    def clean_albumin_creatinine_ratio(self):
        albumin_creatinine_ratio = self.cleaned_data["albumin_creatinine_ratio"]

        if albumin_creatinine_ratio:
            if albumin_creatinine_ratio < 0:
                raise ValidationError(
                    "Urinary Albumin Level (ACR) out of range. Cannot be negative"
                )
            elif albumin_creatinine_ratio > 999:
                raise ValidationError(
                    "Urinary Albumin Level (ACR) out of range. Cannot be above 999 mg/mmol"
                )

        return albumin_creatinine_ratio

    def clean_total_cholesterol(self):
        total_cholesterol = self.cleaned_data["total_cholesterol"]

        if total_cholesterol:
            if total_cholesterol < 2:
                raise ValidationError(
                    "Total Cholesterol Level (mmol/l) out of range. Cannot be below 2"
                )
            elif total_cholesterol > 12:
                raise ValidationError(
                    "Total Cholesterol Level (mmol/l) out of range. Cannot be above 12"
                )

        return total_cholesterol

    """
    Custom clean methods for all fields requiring dates
    """

    def clean_visit_date(self):
        data = self.cleaned_data["visit_date"]

        if data is None:
            raise ValidationError("Visit/Appointment Date must be provided.")

        valid, error = validate_date(
            date_under_examination_field_name="visit_date",
            date_under_examination_label_name="Visit/Appointment Date",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["visit_date"]

    def clean_height_weight_observation_date(self):
        data = self.cleaned_data["height_weight_observation_date"]
        valid, error = validate_date(
            date_under_examination_field_name="height_weight_observation_date",
            date_under_examination_label_name="Observation Date (Height and weight)",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["height_weight_observation_date"]

    def clean_hba1c_date(self):
        data = self.cleaned_data["hba1c_date"]
        valid, error = validate_date(
            date_under_examination_field_name="hba1c_date",
            date_under_examination_label_name="Observation Date: Hba1c Value",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["hba1c_date"]

    def clean_blood_pressure_observation_date(self):
        data = self.cleaned_data["blood_pressure_observation_date"]
        valid, error = validate_date(
            date_under_examination_field_name="blood_pressure_observation_date",
            date_under_examination_label_name="Observation Date (Blood Pressure)",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["blood_pressure_observation_date"]

    def clean_foot_examination_observation_date(self):
        data = self.cleaned_data["foot_examination_observation_date"]
        valid, error = validate_date(
            date_under_examination_field_name="foot_examination_observation_date",
            date_under_examination_label_name="Foot Assessment / Examination Date",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["foot_examination_observation_date"]

    def clean_retinal_screening_observation_date(self):
        data = self.cleaned_data["retinal_screening_observation_date"]
        valid, error = validate_date(
            date_under_examination_field_name="retinal_screening_observation_date",
            date_under_examination=data,
            date_under_examination_label_name="Retinal Screening date",
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["retinal_screening_observation_date"]

    def clean_albumin_creatinine_ratio_date(self):
        data = self.cleaned_data["albumin_creatinine_ratio_date"]
        valid, error = validate_date(
            date_under_examination_field_name="albumin_creatinine_ratio_date",
            date_under_examination_label_name="Observation Date: Urinary Albumin Level",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["albumin_creatinine_ratio_date"]

    def clean_total_cholesterol_date(self):
        data = self.cleaned_data["total_cholesterol_date"]
        valid, error = validate_date(
            date_under_examination_field_name="total_cholesterol_date",
            date_under_examination_label_name="Observation Date: Total Cholesterol Level",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["total_cholesterol_date"]

    def clean_thyroid_function_date(self):
        data = self.cleaned_data["thyroid_function_date"]
        valid, error = validate_date(
            date_under_examination_field_name="thyroid_function_date",
            date_under_examination_label_name="Observation Date: Thyroid Function",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["thyroid_function_date"]

    def clean_coeliac_screen_date(self):
        data = self.cleaned_data["coeliac_screen_date"]
        valid, error = validate_date(
            date_under_examination_field_name="coeliac_screen_date",
            date_under_examination_label_name="Observation Date: Coeliac Disease Screening",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["coeliac_screen_date"]

    def clean_psychological_screening_assessment_date(self):
        data = self.cleaned_data["psychological_screening_assessment_date"]
        valid, error = validate_date(
            date_under_examination_field_name="psychological_screening_assessment_date",
            date_under_examination_label_name="Observation Date - Psychological Screening Assessment",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["psychological_screening_assessment_date"]

    def clean_smoking_cessation_referral_date(self):
        data = self.cleaned_data["smoking_cessation_referral_date"]
        valid, error = validate_date(
            date_under_examination_field_name="smoking_cessation_referral_date",
            date_under_examination_label_name="Date of offer of referral to smoking cessation service (if patient is a current smoker)",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["smoking_cessation_referral_date"]

    def clean_carbohydrate_counting_level_three_education_date(self):
        data = self.cleaned_data["carbohydrate_counting_level_three_education_date"]
        valid, error = validate_date(
            date_under_examination_field_name="carbohydrate_counting_level_three_education_date",
            date_under_examination_label_name="Date of Level 3 carbohydrate counting education received",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["carbohydrate_counting_level_three_education_date"]

    def clean_dietician_additional_appointment_date(self):
        data = self.cleaned_data["dietician_additional_appointment_date"]
        valid, error = validate_date(
            date_under_examination_field_name="dietician_additional_appointment_date",
            date_under_examination_label_name="Date of additional appointment with dietitian",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["dietician_additional_appointment_date"]

    def clean_flu_immunisation_recommended_date(self):
        data = self.cleaned_data["flu_immunisation_recommended_date"]
        valid, error = validate_date(
            date_under_examination_field_name="flu_immunisation_recommended_date",
            date_under_examination_label_name="Date that influenza immunisation was recommended",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["flu_immunisation_recommended_date"]

    def clean_sick_day_rules_training_date(self):
        data = self.cleaned_data["sick_day_rules_training_date"]
        valid, error = validate_date(
            date_under_examination_field_name="sick_day_rules_training_date",
            date_under_examination_label_name="Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["sick_day_rules_training_date"]

    def clean_hospital_admission_date(self):
        data = self.cleaned_data["hospital_admission_date"]
        valid, error = validate_date(
            date_under_examination_field_name="hospital_admission_date",
            date_under_examination_label_name="Start date (Hospital Provider Spell)",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["hospital_admission_date"]

    def clean_hospital_discharge_date(self):
        data = self.cleaned_data["hospital_discharge_date"]
        valid, error = validate_date(
            date_under_examination_field_name="hospital_discharge_date",
            date_under_examination_label_name="Discharge date (Hospital provider spell",
            date_under_examination=data,
            date_of_birth=self.patient.date_of_birth,
            date_of_diagnosis=self.patient.diagnosis_date,
            date_of_death=self.patient.death_date,
        )
        if valid == False:
            raise ValidationError(error)

        return self.cleaned_data["hospital_discharge_date"]

    def handle_async_validation_errors(self):
        # These are calculated fields but we handle them in the form because we want to add validation errors.
        # Conceptually we both "clean" weight and height and derive new fields from them. The actual data is
        # saved in .save() below - this is just for the validation errors.

        for [result_field, fields_to_attach_errors] in [
            ["height_result", ["height"]],
            ["weight_result", ["weight"]],
            ["bmi_result", ["height", "weight"]],
        ]:
            result = getattr(self.async_validation_results, result_field)

            if result and type(result) is ValidationError:
                for field in fields_to_attach_errors:
                    self.add_error(field, result)

    def clean(self):
        cleaned_data = super().clean()

        def round_to_one_decimal_place(value):
            return Decimal(value).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )  # round to 1 decimal place: although the rounding is done in the clean methods for height and weight, this is a final check

        birth_date = self.patient.date_of_birth
        sex = self.patient.sex

        height_weight_observation_date = cleaned_data.get(
            "height_weight_observation_date"
        )

        height = cleaned_data.get("height")
        if height is not None:
            cleaned_data["height"] = height = round_to_one_decimal_place(height)
            # Validate all fields in a measure are present
            measure_must_have_date_and_value(
                height_weight_observation_date,
                "height_weight_observation_date",
                [{"height": height}],
            )

        weight = cleaned_data.get("weight")
        if weight is not None:
            cleaned_data["weight"] = weight = round_to_one_decimal_place(weight)
            # Validate all fields in a measure are present
            measure_must_have_date_and_value(
                height_weight_observation_date,
                "height_weight_observation_date",
                [{"weight": height}],
            )

        if height_weight_observation_date is not None:
            if height is None and weight is None:
                raise ValidationError(
                    "Height and Weight cannot both be empty if Observation Date is filled in"
                )

        # Get centiles for height and weight and bmi if they are present as well as date and sex
        if not getattr(self, "async_validation_results", None):
            self.async_validation_results = validate_visit_sync(
                birth_date=birth_date,
                observation_date=height_weight_observation_date,
                height=height,
                weight=weight,
                sex=sex,
            )

        self.handle_async_validation_errors()

        # Check that the hba1c value is within the correct range
        hba1c = cleaned_data.get("hba1c")
        hba1c_format = cleaned_data.get("hba1c_format")
        hba1c_date = cleaned_data.get("hba1c_date")

        if hba1c is not None:
            if hba1c_format == 1:
                # mmol/mol
                if hba1c < 20:
                    raise ValidationError(
                        {
                            "hba1c": [
                                "Hba1c Value out of range (mmol/mol). Cannot be below 20. Did you mean to enter a DCCT (%) value?"
                            ]
                        }
                    )
                elif hba1c > 195:
                    raise ValidationError(
                        {
                            "hba1c": [
                                "Hba1c Value out of range (mmol/mol). Cannot be above 195"
                            ]
                        }
                    )
            elif hba1c_format == 2:
                # %
                if hba1c < 3:
                    raise ValidationError(
                        {"hba1c": ["Hba1c Value out of range (%). Cannot be below 3"]}
                    )
                elif hba1c > 20:
                    raise ValidationError(
                        {
                            "hba1c": [
                                "Hba1c Value out of range (%). Cannot be above 20. Did you mean to enter an IFCC (mmol/mol) value?"
                            ]
                        }
                    )
        if any([hba1c, hba1c_format, hba1c_date]):
            # Validate all fields in a measure are present if any are present
            measure_must_have_date_and_value(
                hba1c_date,
                "hba1c_date",
                [{"hba1c": hba1c}, {"hba1c_format": hba1c_format}],
            )

        treatment = cleaned_data.get("treatment")
        closed_loop_system = cleaned_data.get("closed_loop_system")
        if any([treatment, closed_loop_system]):
            if treatment:
                if treatment == 3 or treatment == 6:
                    # Insulin pump or pump with drugs
                    all_items_must_be_filled_in(
                        [
                            {"treatment": treatment},
                            {"closed_loop_system": closed_loop_system},
                        ]
                    )
                else:
                    if closed_loop_system:  # No is not selected
                        raise ValidationError(
                            {
                                "closed_loop_system": [
                                    "Closed Loop System must be left empty if selected treatment is not an Insulin Pump or insulin pump therapy with other glucose lowering medications."
                                ]
                            }
                        )
            else:
                raise ValidationError(
                    {
                        "treatment": [
                            "Treatment must be filled in if Closed Loop System is filled in"
                        ]
                    }
                )

        blood_pressure_observation_date = cleaned_data.get(
            "blood_pressure_observation_date"
        )
        systolic_blood_pressure = cleaned_data.get("systolic_blood_pressure")
        diastolic_blood_pressure = cleaned_data.get("diastolic_blood_pressure")
        if any(
            [
                systolic_blood_pressure,
                diastolic_blood_pressure,
                blood_pressure_observation_date,
            ]
        ):
            measure_must_have_date_and_value(
                blood_pressure_observation_date,
                "blood_pressure_observation_date",
                [
                    {"systolic_blood_pressure": systolic_blood_pressure},
                    {"diastolic_blood_pressure": diastolic_blood_pressure},
                ],
            )

        retinal_screening_observation_date = cleaned_data.get(
            "retinal_screening_observation_date"
        )
        retinal_screening_result = cleaned_data.get("retinal_screening_result")
        if any([retinal_screening_observation_date, retinal_screening_result]):
            measure_must_have_date_and_value(
                retinal_screening_observation_date,
                "retinal_screening_observation_date",
                [{"retinal_screening_result": retinal_screening_result}],
            )

        albumin_creatinine_ratio_date = cleaned_data.get(
            "albumin_creatinine_ratio_date"
        )
        albumin_creatinine_ratio = cleaned_data.get("albumin_creatinine_ratio")
        albuminuria_stage = cleaned_data.get("albuminuria_stage")
        if any(
            [albumin_creatinine_ratio_date, albumin_creatinine_ratio, albuminuria_stage]
        ):
            measure_must_have_date_and_value(
                albumin_creatinine_ratio_date,
                "albumin_creatinine_ratio_date",
                [
                    {"albumin_creatinine_ratio": albumin_creatinine_ratio},
                    {"albuminuria_stage": albuminuria_stage},
                ],
            )

        total_cholesterol_date = cleaned_data.get("total_cholesterol_date")
        total_cholesterol = cleaned_data.get("total_cholesterol")
        if any([total_cholesterol_date, total_cholesterol]):
            measure_must_have_date_and_value(
                total_cholesterol_date,
                "total_cholesterol_date",
                [{"total_cholesterol": total_cholesterol}],
            )

        thyroid_function_date = cleaned_data.get("thyroid_function_date")
        thyroid_treatment_status = cleaned_data.get("thyroid_treatment_status")
        if any([thyroid_function_date, thyroid_treatment_status]):
            measure_must_have_date_and_value(
                thyroid_function_date,
                "thyroid_function_date",
                [{"thyroid_treatment_status": thyroid_treatment_status}],
            )

        coeliac_screen_date = cleaned_data.get("coeliac_screen_date")
        gluten_free_diet = cleaned_data.get("gluten_free_diet")
        if any([coeliac_screen_date, gluten_free_diet]):
            measure_must_have_date_and_value(
                coeliac_screen_date,
                "coeliac_screen_date",
                [{"gluten_free_diet": gluten_free_diet}],
            )

        psychological_screening_assessment_date = cleaned_data.get(
            "psychological_screening_assessment_date"
        )
        psychological_additional_support_status = cleaned_data.get(
            "psychological_additional_support_status"
        )
        if any(
            [
                psychological_screening_assessment_date,
                psychological_additional_support_status,
            ]
        ):
            measure_must_have_date_and_value(
                psychological_screening_assessment_date,
                "psychological_screening_assessment_date",
                [
                    {
                        "psychological_additional_support_status": psychological_additional_support_status
                    }
                ],
            )

        smoking_cessation_referral_date = cleaned_data.get(
            "smoking_cessation_referral_date"
        )
        smoking_status = cleaned_data.get("smoking_status")
        if smoking_status:
            if smoking_status == 2:  # Current  smoking status: must supply a date
                measure_must_have_date_and_value(
                    smoking_cessation_referral_date,
                    "smoking_cessation_referral_date",
                    [{"smoking_status": smoking_status}],
                )
            else:
                if smoking_cessation_referral_date is not None:
                    raise ValidationError(
                        {
                            "smoking_cessation_referral_date": [
                                "Smoking Cessation Referral Date must be left empty if patient is not a current smoker or status is unknown."
                            ]
                        }
                    )
        else:
            if smoking_cessation_referral_date is not None:
                raise ValidationError(
                    {
                        "smoking_cessation_referral_date": [
                            "Smoking Cessation Referral Date must be left empty if Smoking Status is not filled in"
                        ]
                    }
                )

        dietician_additional_appointment_offered = cleaned_data.get(
            "dietician_additional_appointment_offered"
        )
        dietician_additional_appointment_date = cleaned_data.get(
            "dietician_additional_appointment_date"
        )
        if dietician_additional_appointment_offered is not None:
            if dietician_additional_appointment_offered == 1:
                measure_must_have_date_and_value(
                    dietician_additional_appointment_date,
                    "dietician_additional_appointment_date",
                    [
                        {
                            "dietician_additional_appointment_offered": dietician_additional_appointment_offered
                        }
                    ],
                )

        if dietician_additional_appointment_date is not None and (
            dietician_additional_appointment_offered is None
            or dietician_additional_appointment_offered == 2
            or dietician_additional_appointment_offered == 3
        ):  # No or Unknown
            raise ValidationError(
                {
                    "dietician_additional_appointment_date": [
                        "'Was the patient offered an additional appointment with a paediatric dietitian?' must be completed if 'Date of additional appointment with dietitian' is filled in"
                    ]
                }
            )

        sick_day_rules_training_date = cleaned_data.get("sick_day_rules_training_date")
        ketone_meter_training = cleaned_data.get("ketone_meter_training")

        if ketone_meter_training is not None:
            if ketone_meter_training == 1:
                measure_must_have_date_and_value(
                    sick_day_rules_training_date,
                    "sick_day_rules_training_date",
                    [{"ketone_meter_training": ketone_meter_training}],
                )
            else:
                if sick_day_rules_training_date is not None:
                    raise ValidationError(
                        {
                            "ketone_meter_training": [
                                "'Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia is only needed if patient is using ketone testing equipment."
                            ],
                        },
                    )
        else:
            if sick_day_rules_training_date is not None:
                raise ValidationError(
                    {
                        "ketone_meter_training": [
                            "'Was the patient using (or trained to use) blood ketone testing equipment at time of visit?' must be completed if Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia has been provided."
                        ],
                    }
                )

        hospital_admission_date = cleaned_data.get("hospital_admission_date")
        hospital_discharge_date = cleaned_data.get("hospital_discharge_date")
        hospital_admission_reason = cleaned_data.get("hospital_admission_reason")
        dka_additional_therapies = cleaned_data.get("dka_additional_therapies")
        hospital_admission_other = cleaned_data.get("hospital_admission_other")
        if any(
            [
                hospital_admission_date,
                hospital_discharge_date,
                hospital_admission_reason,
                dka_additional_therapies,
                hospital_admission_other,
            ]
        ):
            if hospital_admission_reason is not None:
                if hospital_admission_reason == 2:  # DKA
                    all_items_must_be_filled_in(
                        [
                            {"hospital_admission_date": hospital_admission_date},
                            {"hospital_discharge_date": hospital_discharge_date},
                            {"hospital_admission_reason": hospital_admission_reason},
                            {"dka_additional_therapies": dka_additional_therapies},
                        ]
                    )
                elif hospital_admission_reason == 6:  # Other
                    all_items_must_be_filled_in(
                        [
                            {"hospital_admission_date": hospital_admission_date},
                            {"hospital_discharge_date": hospital_discharge_date},
                            {"hospital_admission_reason": hospital_admission_reason},
                            {"hospital_admission_other": hospital_admission_other},
                        ]
                    )
                else:
                    all_items_must_be_filled_in(
                        [
                            {"hospital_admission_date": hospital_admission_date},
                            {"hospital_discharge_date": hospital_discharge_date},
                            {"hospital_admission_reason": hospital_admission_reason},
                        ]
                    )
                    if hospital_admission_other is not None:
                        raise ValidationError(
                            {
                                "hospital_admission_other": [
                                    "Hospital Admission Reason must be 'Other' if 'Other' has been completed."
                                ]
                            }
                        )
                    if dka_additional_therapies is not None:
                        raise ValidationError(
                            {
                                "dka_additional_therapies": [
                                    "Hospital Admission Reason must be 'DKA' if 'DKA Additional Therapies' has been completed."
                                ]
                            }
                        )
            else:
                # No hospital admission reason selected
                all_items_must_be_filled_in(
                    [
                        {"hospital_admission_date": hospital_admission_date},
                        {"hospital_discharge_date": hospital_discharge_date},
                        {"hospital_admission_reason": hospital_admission_reason},
                    ]
                )

            if hospital_admission_other is not None and hospital_admission_reason != 6:
                raise ValidationError(
                    {
                        "hospital_admission_other": [
                            "Hospital Admission Reason must be 'Other' if 'Other' is filled in"
                        ]
                    }
                )

            if (
                hospital_admission_date is not None
                and hospital_discharge_date is not None
            ):
                if hospital_admission_date > hospital_discharge_date:
                    raise ValidationError(
                        {
                            "hospital_admission_date": [
                                "Hospital Admission Date cannot be after Hospital Discharge Date"
                            ]
                        }
                    )

        return cleaned_data

    def save(self, commit=True):
        # We deliberately don't call super.save here as it throws ValueError on validation errors
        # and for CSV uploads we don't want that to stop us. As of Django 5.1.5 it doesn't do anything
        # else other than saving the model or setting up save_m2m. We don't use the latter so
        # I haven't implemented it here. The risk is that future versions of Django will add more
        # behaviour that we miss out on.

        if getattr(self, "async_validation_results"):
            self.instance.bmi = self.async_validation_results.bmi

            for field_prefix in ["height", "weight", "bmi"]:
                result = getattr(
                    self.async_validation_results, f"{field_prefix}_result"
                )

                if result and not type(result) is ValidationError:
                    setattr(self.instance, f"{field_prefix}_centile", result.centile)
                    setattr(self.instance, f"{field_prefix}_sds", result.sds)

        if commit:
            self.instance.save()

        return self.instance


def measure_must_have_date_and_value(date_field, date_field_name, field_list):
    """
    Validate that a measure has a date and a value
    The date_field is the date the measure was taken
    The kwargs is a variable number of key value pairs where the key is the name of the measure and the value is value of the measure
    """
    errors = {}
    field_name_list = []
    for field in field_list:
        for key, value in field.items():
            heading = return_heading_model_field(key)
            field_name_list.append(heading)
            if value is None:
                errors.update(
                    {
                        f"{key}": [
                            f"Missing item. {heading} and the associated date must all be completed."
                        ]
                    }
                )
    field_name_list = ", ".join(field_name_list)
    if date_field is None:
        errors.update(
            {
                date_field_name: [
                    f"Missing date. {field_name_list} and the associated date must all be completed."
                ]
            }
        )
    if errors:
        raise ValidationError(errors)


"""
Helper functions for validation in the clean method
"""


def all_items_must_be_filled_in(field_list):
    """
    Validate that all items in a list are filled in
    """
    errors = {}
    field_name_list = []
    for field in field_list:
        for key, value in field.items():
            heading = return_heading_model_field(key)
            field_name_list.append(heading)
            if value is None:
                errors.update(
                    {f"{key}": [f"Missing item. {heading} must also be completed."]}
                )
    field_name_list = ", ".join(field_name_list)
    if errors:
        raise ValidationError(errors)


def return_heading_model_field(field):
    """
    Return the heading for a given model field
    """

    for heading in CSV_HEADING_OBJECTS:
        if heading["model_field"] == field:
            return heading["heading"]
    return None
