# python imports
from datetime import date
import logging
import asyncio
import collections

# django imports
from django.apps import apps
from django.utils import timezone
from django.core.exceptions import ValidationError

# third part imports
import pandas as pd
import numpy as np
import httpx
from ..general_functions.write_errors_to_xlsx import write_errors_to_xlsx

# Logging setup
logger = logging.getLogger(__name__)

from ..forms.patient_form import PatientForm
from ..forms.visit_form import VisitForm
from ..forms.external_patient_validators import validate_patient_async


async def csv_upload(user, dataframe, csv_file, pdu_pz_code):
    """
    Processes standardised NPDA csv file and persists results in NPDA tables
    Returns the empty dict if successful, otherwise ValidationErrors indexed by the row they occurred at
    Also return the dataframe for later summary purposes
    """
    Patient = apps.get_model("npda", "Patient")
    Transfer = apps.get_model("npda", "Transfer")
    Visit = apps.get_model("npda", "Visit")
    Submission = apps.get_model("npda", "Submission")
    PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")

    # get the PDU object
    # TODO #249 MRB: handle case where PDU does not exist
    pdu = await PaediatricDiabetesUnit.objects.aget(pz_code=pdu_pz_code)

    # Set previous submission to inactive
    if await Submission.objects.filter(
        paediatric_diabetes_unit__pz_code=pdu.pz_code,
        audit_year=date.today().year,
        submission_active=True,
    ).aexists():
        original_submission = await Submission.objects.filter(
            submission_active=True,
            paediatric_diabetes_unit__pz_code=pdu.pz_code,
            audit_year=date.today().year,
        ).aget()  # there can be only one of these - store it in a variable in case we need to revert
    else:
        original_submission = None

    # Create new submission for the audit year
    # It is not possble to create submissions in years other than the current year
    try:
        new_submission = await Submission.objects.acreate(
            paediatric_diabetes_unit=pdu,
            audit_year=date.today().year,
            submission_date=timezone.now(),
            submission_by=user,  # user is the user who is logged in. Passed in as a parameter
            submission_active=True,
        )

        if csv_file:
            # save the csv file with a custom name
            new_filename = (
                f"{pdu.pz_code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

            # save=False so it doesn't try to save the parent, which would cause an error in an async context
            # we save immediately after this anyway
            new_submission.csv_file.save(new_filename, csv_file, save=False)

        await new_submission.asave()

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
            original_submission_patient_count = await Patient.objects.filter(
                submissions=original_submission
            ).acount()
            print(
                f"Deleting patients from previous submission: {original_submission_patient_count}"
            )
            await Patient.objects.filter(submissions=original_submission).adelete()
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
            await original_submission.asave()  # this action will delete the csv file also as per the save method in the model
        except Exception as e:
            raise ValidationError(
                {"csv_upload": "Error deactivating previous submission"}
            )

    def csv_value_to_model_value(model_field, value):
        if pd.isnull(value):
            return None

        # # Pandas is returning 0 for empty cells in integer columns
        # if value == 0:
        #     return None

        # Pandas will convert an integer column to float if it contains missing values
        # http://pandas.pydata.org/pandas-docs/stable/user_guide/gotchas.html#missing-value-representation-for-numpy-types
        # if pd.api.types.is_float(value) and model_field.choices:
        #     return int(value)

        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime().date()

        # if model_field.choices:
        #     # If the model field has choices, we need to convert the value to the correct type otherwise 1, 2 will be saved as booleans
        #     return model_field.to_python(value)

        return value

    def parse_row_using_model(row, model, mapping):
        model_values = {}
        field_errors = {}

        for model_field_name, csv_field in mapping.items():
            try:
                model_field = model._meta.get_field(model_field_name)
                csv_value = row[csv_field]

                # print(f"csv_value: {csv_value}, model_field_name: {model_field_name}")

                model_value = csv_value_to_model_value(model_field, csv_value)
                model_values[model_field_name] = model_value
            except ValidationError as e:
                field_errors[model_field_name] = e

        return (model_values, field_errors)

    def validate_transfer(row):
        return parse_row_using_model(
            row,
            Transfer,
            {
                "date_leaving_service": "Date of leaving service",
                "reason_leaving_service": "Reason for leaving service",
            },
        )

    async def validate_patient_using_form(row, async_client):
        (fields, field_errors) = parse_row_using_model(
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
        form.async_validation_results = await validate_patient_async(
            postcode=fields["postcode"],
            gp_practice_ods_code=fields["gp_practice_ods_code"],
            gp_practice_postcode=None,
            async_client=async_client,
        )

        return (form, field_errors)

    def validate_visit_using_form(patient, row):
        (fields, field_errors) = parse_row_using_model(
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
        return (form, field_errors)

    async def validate_rows(rows, async_client):
        first_row = rows.iloc[0]
        patient_row_index = first_row["row_index"]

        (transfer_fields, transfer_field_errors) = validate_transfer(first_row)
        (patient_form, patient_field_errors) = await validate_patient_using_form(
            first_row, async_client
        )

        visits = []

        for _, row in rows.iterrows():
            (visit_form, visit_field_errors) = validate_visit_using_form(
                patient_form.instance, row
            )
            visits.append((visit_form, visit_field_errors, row["row_index"]))

        first_row_field_errors = transfer_field_errors | patient_field_errors

        return (
            patient_form,
            transfer_fields,
            patient_row_index,
            first_row_field_errors,
            visits,
        )

    def create_instance(model, form):
        # We want to retain fields even if they're invalid so that we can return them to the user
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

    async def validate_rows_in_parallel(rows_by_patient, async_client):
        tasks = []

        async with asyncio.TaskGroup() as tg:
            for _, rows in visits_by_patient:
                task = tg.create_task(validate_rows(rows, async_client))
                tasks.append(task)

        return [task.result() for task in tasks]

    # Remember the original row number to help users find where the problem was in the CSV
    dataframe["row_index"] = np.arange(dataframe.shape[0])

    # We only one to create one patient per NHS number and we can't create their visits if we fail to save the patient model
    visits_by_patient = dataframe.groupby("NHS Number", sort=False, dropna=False)

    # Gather all errors indexed by row number and the field that caused them (__all__ if we don't know which one)
    # dict[number, dict[str, list[ValidationError]]]
    errors_to_return = collections.defaultdict(lambda: collections.defaultdict(list))

    async with httpx.AsyncClient() as async_client:
        validation_results_by_patient = await validate_rows_in_parallel(
            visits_by_patient, async_client
        )

        for (
            patient_form,
            transfer_fields,
            patient_row_index,
            first_row_field_errors,
            visits,
        ) in validation_results_by_patient:
            # Errors parsing the Transfer or Patient fields
            for field, error in first_row_field_errors.items():
                errors_to_return[patient_row_index][field].append(error)

            # Errors validating the Patient fields
            for field, error in patient_form.errors.as_data().items():
                errors_to_return[patient_row_index][field].append(error)

            try:
                patient = create_instance(Patient, patient_form)

                # We don't call PatientForm.save as there's no async version so we have to set this manually
                patient.index_of_multiple_deprivation_quintile = (
                    patient_form.async_validation_results.index_of_multiple_deprivation_quintile
                )

                await patient.asave()

                # add the patient to a new Transfer instance
                transfer_fields["paediatric_diabetes_unit"] = pdu
                transfer_fields["patient"] = patient
                await Transfer.objects.acreate(**transfer_fields)

                await new_submission.patients.aadd(patient)
            except Exception as error:
                # We don't know what field caused the error so add to __all__
                errors_to_return[patient_row_index]["__all__"].append(error)

            for visit_form, visit_field_errors, visit_row_index in visits:
                # Errors parsing the Visit fields
                for field, error in visit_field_errors.items():
                    errors_to_return[visit_row_index][field].append(error)

                # Errors validating the Visit fields
                for field, error in visit_form.errors.as_data().items():
                    errors_to_return[visit_row_index][field].append(error)

                try:
                    visit = create_instance(Visit, visit_form)
                    visit.patient = patient
                    await visit.asave()
                except Exception as error:
                    errors_to_return[visit_row_index]["__all__"].append(error)

    # Copy csv to a styled xlsx.
    _ = write_errors_to_xlsx(errors_to_return, new_submission)
    return errors_to_return
