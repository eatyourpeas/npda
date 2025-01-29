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
                f"'{data}' is not a value for 'Gluten Free Diet'. Please select one of {options}."
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
            if albumin_creatinine_ratio < 20:
                raise ValidationError(
                    "Urinary Albumin Level (ACR) out of range. Cannot be below 0"
                )
            elif albumin_creatinine_ratio > 50:
                raise ValidationError(
                    "Urinary Albumin Level (ACR) out of range. Cannot be above 50"
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

        observation_date = cleaned_data.get("height_weight_observation_date")

        height = cleaned_data.get("height")
        if height is not None:
            cleaned_data["height"] = height = round_to_one_decimal_place(height)

        weight = cleaned_data.get("weight")
        if weight is not None:
            cleaned_data["weight"] = weight = round_to_one_decimal_place(weight)

        if not getattr(self, "async_validation_results", None):
            self.async_validation_results = validate_visit_sync(
                birth_date=birth_date,
                observation_date=observation_date,
                height=height,
                weight=weight,
                sex=sex,
            )

        self.handle_async_validation_errors()

        # Check that the hba1c value is within the correct range
        hba1c_value = cleaned_data["hba1c"]
        hba1c_format = cleaned_data["hba1c_format"]

        if hba1c_value is not None:
            if hba1c_format == 1:
                # mmol/mol
                if hba1c_value < 20:
                    raise ValidationError(
                        "Hba1c Value out of range (mmol/mol). Cannot be below 20"
                    )
                elif hba1c_value > 195:
                    raise ValidationError(
                        "Hba1c Value out of range (mmol/mol). Cannot be above 195"
                    )
            elif hba1c_format == 2:
                # %
                if hba1c_value < 3:
                    raise ValidationError(
                        "Hba1c Value out of range (%). Cannot be below 3"
                    )
                elif hba1c_value > 20:
                    raise ValidationError(
                        "Hba1c Value out of range (%). Cannot be above 20"
                    )

        return cleaned_data

    def save(self):
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

        self.instance.save()

        return self.instance
