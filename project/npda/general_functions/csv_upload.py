# python imports
from datetime import date
from dataclasses import dataclass
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

# RCPCH imports
from ...constants.csv_headings import (
    ALL_DATES,
    CSV_HEADINGS
)

# Logging setup
logger = logging.getLogger(__name__)
from ..forms.patient_form import PatientForm
from ..forms.visit_form import VisitForm
from ..forms.external_patient_validators import validate_patient_async


@dataclass
class ParsedCSVFile:
    df: pd.DataFrame
    missing_columns: list[str]
    additional_columns: list[str]
    duplicate_columns: list[str]


def read_csv(csv_file) -> ParsedCSVFile:
    df = pd.read_csv(csv_file)

    # Remove leading and trailing whitespace on column names
    # The template published on the RCPCH website has trailing spaces on 'Observation Date: Thyroid Function '
    df.columns = df.columns.str.strip()

    for column in ALL_DATES:
        df[column] = pd.to_datetime(df[column], format="%d/%m/%Y")

    csv_headings = [heading["heading"] for heading in CSV_HEADINGS]

    missing_columns = [column for column in csv_headings if not column in df.columns]
    additional_columns = [column for column in df.columns if not column in csv_headings]

    return ParsedCSVFile(df, missing_columns, additional_columns, [])


async def csv_upload(user, dataframe, csv_file, pdu_pz_code):
    """
    Processes standardised NPDA csv file and persists results in NPDA tables
    Returns the empty dict if successful, otherwise ValidationErrors indexed by the row they occurred at 
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
            new_filename = f"{pdu.pz_code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"

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
            original_submission_patient_count = await Patient.objects.filter(submissions=original_submission).acount()
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

    def row_to_dict(row, model):
        ret = {}

        for entry in CSV_HEADINGS:
            if "model" in entry and entry["model"] == model:
                model_field_name = entry["model_field"]
                model_field_definition = model._meta.get_field(model_field_name)

                csv_value = row[entry["heading"]]
                model_field_value = csv_value_to_model_value(model_field_definition, csv_value)

                ret[model_field_name] = model_field_value

        return ret

    def validate_transfer(row):
        return row_to_dict(
            row,
            Transfer
        ) | {"paediatric_diabetes_unit": pdu}

    async def validate_patient_using_form(row, async_client):
        fields = row_to_dict(
            row,
            Patient
        )
        
        form = PatientForm(fields)
        form.async_validation_results = await validate_patient_async(
                postcode=fields["postcode"],
                gp_practice_ods_code=fields["gp_practice_ods_code"],
                gp_practice_postcode=None,
                async_client=async_client
        )

        return form

    def validate_visit_using_form(patient, row):
        fields = row_to_dict(
            row,
            Visit,
        )

        form = VisitForm(data=fields, initial={"patient": patient})
        return form

    async def validate_rows(rows, async_client):
        first_row = rows.iloc[0]
        patient_row_index = first_row["row_index"]

        transfer_fields = validate_transfer(first_row)
        patient_form = await validate_patient_using_form(first_row, async_client)

        visits = rows.apply(
            lambda row: (validate_visit_using_form(patient_form.instance, row), row["row_index"]),
            axis=1,
        )

        return (patient_form, transfer_fields, patient_row_index, visits)

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
        validation_results_by_patient = await validate_rows_in_parallel(visits_by_patient, async_client)

        for (patient_form, transfer_fields, patient_row_index, visits) in validation_results_by_patient:
            for field, error in patient_form.errors.as_data().items():
                errors_to_return[patient_row_index][field].append(error)

            try:
                patient = create_instance(Patient, patient_form)

                # We don't call PatientForm.save as there's no async version so we have to set this manually
                patient.index_of_multiple_deprivation_quintile = patient_form.async_validation_results.index_of_multiple_deprivation_quintile

                await patient.asave()

                # add the patient to a new Transfer instance
                transfer_fields["paediatric_diabetes_unit"] = pdu
                transfer_fields["patient"] = patient
                await Transfer.objects.acreate(**transfer_fields)

                await new_submission.patients.aadd(patient)
            except Exception as error:
                # We don't know what field caused the error so add to __all__
                errors_to_return[patient_row_index]["__all__"].append(error)

            for (visit_form, visit_row_index) in visits:
                for field, error in visit_form.errors.as_data().items():
                    errors_to_return[visit_row_index][field].append(error)

                try:
                    visit = create_instance(Visit, visit_form)
                    visit.patient = patient
                    await visit.asave()
                except Exception as error:
                    errors_to_return[visit_row_index]["__all__"].append(error)
        
        return errors_to_return
