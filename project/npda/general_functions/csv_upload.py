# python imports
from datetime import date
import logging

# django imports
from django.apps import apps
from django.utils import timezone
from django.core.exceptions import ValidationError

# third part imports
import pandas as pd
import numpy as np

# RCPCH imports
from ...constants import (
    ALL_DATES,
)

# Logging setup
logger = logging.getLogger(__name__)
from ..forms.patient_form import PatientForm
from ..forms.visit_form import VisitForm


def read_csv(csv_file):
    return pd.read_csv(
        csv_file, parse_dates=ALL_DATES, dayfirst=True, date_format="%d/%m/%Y"
    )

def csv_upload(user, dataframe, csv_file, pdu_pz_code):
    """
    Processes standardised NPDA csv file and persists results in NPDA tables

    accepts CSV file with standardised column names

    return True if successful, False with error message if not
    """
    Patient = apps.get_model("npda", "Patient")
    Transfer = apps.get_model("npda", "Transfer")
    Visit = apps.get_model("npda", "Visit")
    Submission = apps.get_model("npda", "Submission")
    PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")

    # get the PDU object
    # TODO #249 MRB: handle case where PDU does not exist
    pdu = PaediatricDiabetesUnit.objects.get(pz_code=pdu_pz_code)

    # Set previous submission to inactive
    if Submission.objects.filter(
        paediatric_diabetes_unit__pz_code=pdu.pz_code,
        audit_year=date.today().year,
        submission_active=True,
    ).exists():
        original_submission = Submission.objects.filter(
            submission_active=True,
            paediatric_diabetes_unit__pz_code=pdu.pz_code,
            audit_year=date.today().year,
        ).get()  # there can be only one of these - store it in a variable in case we need to revert
    else:
        original_submission = None

    print(f"Original submission: {original_submission}")

    # Create new submission for the audit year
    # It is not possble to create submissions in years other than the current year
    try:
        new_submission = Submission.objects.create(
            paediatric_diabetes_unit=pdu,
            audit_year=date.today().year,
            submission_date=timezone.now(),
            submission_by=user,  # user is the user who is logged in. Passed in as a parameter
            submission_active=True,
        )

        if csv_file:
            # save the csv file with a custom name
            new_filename = f"{pdu.pz_code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
            new_submission.csv_file.save(new_filename, csv_file)
        
        new_submission.save()

    except Exception as e:
        logger.error(f"Error creating new submission: {e}")
        # the new submission was not created  - no action required as the previous submission is still active
        raise ValidationError(
            {
                "csv_upload": "Error creating new submission. The old submission has been restored."
            }
        )

    # now can delete all patients and visits from the previous active submission
    if original_submission:
        try:
            print(
                f"Deleting patients from previous submission: {Patient.objects.filter(submissions=original_submission).count()}"
            )
            Patient.objects.filter(submissions=original_submission).delete()
        except Exception as e:
            raise ValidationError(
                {"csv_upload": "Error deleting patients from previous submission"}
            )

    # now can delete the any previous active submission's csv file (if it exists)
    # and remove the path from the field by setting it to None
    # the rest of the submission will be retained
    if original_submission:
        original_submission.submission_active = False
        try:
            original_submission.save()  # this action will delete the csv file also as per the save method in the model
        except Exception as e:
            raise ValidationError(
                {"csv_upload": "Error deactivating previous submission"}
            )

    def csv_value_to_model_value(model_field, value):
        if pd.isnull(value):
            return None

        # Pandas is returning 0 for empty cells in integer columns
        if value == 0:
            return None

        # Pandas will convert an integer column to float if it contains missing values
        # http://pandas.pydata.org/pandas-docs/stable/user_guide/gotchas.html#missing-value-representation-for-numpy-types
        if pd.api.types.is_float(value) and model_field.choices:
            return int(value)

        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime().date()

        if model_field.choices:
            # If the model field has choices, we need to convert the value to the correct type otherwise 1, 2 will be saved as booleans
            return model_field.to_python(value)

        return value

    def row_to_dict(row, model, mapping):
        return {
            model_field: csv_value_to_model_value(
                model._meta.get_field(model_field), row[csv_field]
            )
            for model_field, csv_field in mapping.items()
        }

    def validate_transfer(row):
        # TODO MRB: do something with transfer_errors
        return row_to_dict(
            row,
            Transfer,
            {
                "date_leaving_service": "Date of leaving service",
                "reason_leaving_service": "Reason for leaving service",
            },
        ) | {"paediatric_diabetes_unit": pdu}

    def validate_patient_using_form(row):

        fields = row_to_dict(
            row,
            Patient,
            {
                "nhs_number": "NHS Number",
                "date_of_birth": "Date of Birth",
                "postcode": "Postcode of usual address",
                "sex": "Stated gender",
                "ethnicity": "Ethnic Category",
                "diabetes_type": "Diabetes Type",
                "gp_practice_ods_code": "GP Practice Code",
                "diagnosis_date": "Date of Diabetes Diagnosis",
                "death_date": "Death Date",
            },
        )
        form = PatientForm(fields)
        assign_original_row_indices_to_errors(form, row)
        return form

    def validate_visit_using_form(patient, row):

        fields = row_to_dict(
            row,
            Visit,
            {
                "visit_date": "Visit/Appointment Date",
                "height": "Patient Height (cm)",
                "weight": "Patient Weight (kg)",
                "height_weight_observation_date": "Observation Date (Height and weight)",
                "hba1c_format": "HbA1c result format",
                "hba1c_date": "Observation Date: Hba1c Value",
                "treatment": "Diabetes Treatment at time of Hba1c measurement",
                "closed_loop_system": "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
                "glucose_monitoring": "At the time of HbA1c measurement, in addition to standard blood glucose monitoring (SBGM), was the patient using any other method of glucose monitoring?",
                "systolic_blood_pressure": "Systolic Blood Pressure",
                "diastolic_blood_pressure": "Diastolic Blood pressure",
                "blood_pressure_observation_date": "Observation Date (Blood Pressure)",
                "foot_examination_observation_date": "Foot Assessment / Examination Date",
                "retinal_screening_observation_date": "Retinal Screening date",
                "retinal_screening_result": "Retinal Screening Result",
                "albumin_creatinine_ratio": "Urinary Albumin Level (ACR)",
                "albumin_creatinine_ratio_date": "Observation Date: Urinary Albumin Level",
                "albuminuria_stage": "Albuminuria Stage",
                "total_cholesterol": "Total Cholesterol Level (mmol/l)",
                "total_cholesterol_date": "Observation Date: Total Cholesterol Level",
                "thyroid_function_date": "Observation Date: Thyroid Function",
                "thyroid_treatment_status": "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
                "coeliac_screen_date": "Observation Date: Coeliac Disease Screening",
                "gluten_free_diet": "Has the patient been recommended a Gluten-free diet?",
                "psychological_screening_assessment_date": "Observation Date - Psychological Screening Assessment",
                "psychological_additional_support_status": "Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?",
                "smoking_status": "Does the patient smoke?",
                "smoking_cessation_referral_date": "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
                "carbohydrate_counting_level_three_education_date": "Date of Level 3 carbohydrate counting education received",
                "dietician_additional_appointment_offered": "Was the patient offered an additional appointment with a paediatric dietitian?",
                "dietician_additional_appointment_date": "Date of additional appointment with dietitian",
                "ketone_meter_training": "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
                "flu_immunisation_recommended_date": "Date that influenza immunisation was recommended",
                "sick_day_rules_training_date": "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
                "hospital_admission_date": "Start date (Hospital Provider Spell)",
                "hospital_discharge_date": "Discharge date (Hospital provider spell)",
                "hospital_admission_reason": "Reason for admission",
                "dka_additional_therapies": "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
                "hospital_admission_other": "Only complete if OTHER selected: Reason for admission (free text)",
            },
        )

        form = VisitForm(data=fields, initial={"patient": patient})
        assign_original_row_indices_to_errors(form, row)
        return form

    def assign_original_row_indices_to_errors(form, row):
        for _, errors in form.errors.as_data().items():
            for error in errors:
                error.original_row_index = row["row_index"]

    def validate_rows(rows):
        first_row = rows.iloc[0]

        transfer_fields = validate_transfer(first_row)
        patient_form = validate_patient_using_form(first_row)

        visits = rows.apply(
            lambda row: validate_visit_using_form(patient_form.instance, row),
            axis=1,
        )

        return (patient_form, transfer_fields, visits)

    def gather_errors(form):
        ret = {}

        for field, errors in form.errors.as_data().items():
            for error in errors:
                errors_for_field = []

                if field in ret:
                    errors_for_field = ret[field]

                errors_for_field.append(error)

                ret[field] = errors_for_field

        return ret

    def has_error_that_would_fail_save(errors):
        for _, errors in errors.items():
            for error in errors:
                if error.code in ["required", "null"]:
                    return True

    def create_instance(model, form):
        # We want to retain fields even if they're invalid so that we can edit them in the UI
        # Use the field value from cleaned_data, falling back to data if it's not there
        if form.is_valid():
            data = form.cleaned_data
        else:
            data = form.data
        instance = model(**data)
        instance.is_valid = form.is_valid()
        instance.errors = (
            None if form.is_valid() else form.errors.get_json_data(escape_html=True)
        )

        return instance

    # We only one to create one patient per NHS number
    # Remember the original row number to help users find where the problem was in the CSV
    dataframe["row_index"] = np.arange(dataframe.shape[0])

    visits_by_patient = dataframe.groupby("NHS Number", sort=False, dropna=False)

    errors_to_return = {}

    for _, rows in visits_by_patient:
        (patient_form, transfer_fields, visits) = validate_rows(rows)

        errors_to_return = errors_to_return | gather_errors(patient_form)

        for visit_form in visits:
            errors_to_return = errors_to_return | gather_errors(visit_form)

        if not has_error_that_would_fail_save(errors_to_return):
            patient = create_instance(Patient, patient_form)
            patient.save()

            # add the patient to a new Transfer instance
            transfer_fields["paediatric_diabetes_unit"] = pdu
            transfer_fields["patient"] = patient
            Transfer.objects.create(**transfer_fields)

            new_submission.patients.add(patient)

            for visit_form in visits:
                visit = create_instance(Visit, visit_form)
                visit.patient = patient
                visit.save()

    if errors_to_return:
        raise ValidationError(errors_to_return)
