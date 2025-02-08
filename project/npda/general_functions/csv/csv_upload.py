# python imports
from datetime import date
from asgiref.sync import sync_to_async
import logging
import asyncio
import collections
import json

# django imports
from django.apps import apps
from django.utils import timezone
from django.core.exceptions import ValidationError

# third part imports
import pandas as pd
import numpy as np
import httpx

# RCPCH imports
from project.constants import (
    CSV_HEADING_OBJECTS,
    UNIQUE_IDENTIFIER_ENGLAND,
    UNIQUE_IDENTIFIER_JERSEY,
)

# Logging setup
logger = logging.getLogger(__name__)

from project.npda.forms.patient_form import PatientForm
from project.npda.forms.visit_form import VisitForm
from project.npda.forms.external_patient_validators import validate_patient_async
from project.npda.forms.external_visit_validators import validate_visit_async


async def csv_upload(
    user, dataframe, csv_file_name, csv_file_bytes, pdu_pz_code, audit_year
):
    """
    Processes standardised NPDA csv file and persists results in NPDA tables
    Returns the empty dict if successful, otherwise ValidationErrors indexed by the row they occurred at
    """

    # Get the models
    Patient = apps.get_model("npda", "Patient")
    Transfer = apps.get_model("npda", "Transfer")
    Visit = apps.get_model("npda", "Visit")
    Submission = apps.get_model("npda", "Submission")
    PaediatricDiabetesUnit = apps.get_model("npda", "PaediatricDiabetesUnit")

    if pdu_pz_code == "PZ248":
        CSV_HEADINGS = UNIQUE_IDENTIFIER_JERSEY + CSV_HEADING_OBJECTS
    else:
        CSV_HEADINGS = UNIQUE_IDENTIFIER_ENGLAND + CSV_HEADING_OBJECTS

    # Helper functions
    def csv_value_to_model_value(model_field, value):
        if pd.isnull(value):
            return None

        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime().date()

        # Pass Django forms native Python values not numpy ones
        # https://github.com/rcpch/national-paediatric-diabetes-audit/issues/425
        return value.item() if isinstance(value, np.generic) else value

    def row_to_dict(row, model):
        ret = {}

        for entry in CSV_HEADINGS:
            if "model" in entry and apps.get_model("npda", entry["model"]) == model:
                model_field_name = entry["model_field"]
                model_field_definition = model._meta.get_field(model_field_name)

                csv_value = row[entry["heading"]]
                model_field_value = csv_value_to_model_value(
                    model_field_definition, csv_value
                )

                ret[model_field_name] = model_field_value

        return ret

    def validate_transfer(row):
        return row_to_dict(row, Transfer) | {"paediatric_diabetes_unit": pdu}

    async def validate_patient_using_form(row, async_client):
        fields = row_to_dict(row, Patient)

        form = PatientForm(fields)
        form.async_validation_results = await validate_patient_async(
            postcode=fields["postcode"],
            gp_practice_ods_code=fields["gp_practice_ods_code"],
            gp_practice_postcode=None,
            async_client=async_client,
        )

        return form

    async def validate_visit_using_form(patient_form, row, async_client):
        fields = row_to_dict(
            row,
            Visit,
        )

        form = VisitForm(data=fields, initial={"patient": patient_form.instance})
        form.async_validation_results = await validate_visit_async(
            birth_date=patient_form.cleaned_data.get("date_of_birth"),
            observation_date=fields["height_weight_observation_date"],
            height=fields["height"],
            weight=fields["weight"],
            sex=patient_form.cleaned_data.get("sex"),
            async_client=async_client,
        )

        return form

    def retain_errors_and_invalid_field_data(form):
        # We want to retain fields even if they're invalid so that we can return them to the user
        # Use the field value from cleaned_data, falling back to data if it's not there
        for key, value in form.cleaned_data.items():
            setattr(form.instance, key, value)

        for key, value in form.data.items():
            if key not in form.cleaned_data:
                setattr(form.instance, key, value)

        form.instance.is_valid = form.is_valid()
        form.instance.errors = (
            None if form.is_valid() else form.errors.get_json_data(escape_html=True)
        )

    def record_errors_from_form(errors_to_return, row_index, form):
        for field, errors in form.errors.as_data().items():
            for error in errors:
                errors_to_return[row_index][field].extend(error.messages)

    def do_not_save_patient_if_no_unique_identifier(patient_form):
        if (
            patient_form.cleaned_data.get("nhs_number") is None
            and patient_form.cleaned_data.get("unique_reference_number") is None
        ):
            patient = patient_form.save(commit=False)
        else:
            patient = patient_form.save(
                commit=True
            )  # save the patient if there is a unique identifier

        return patient

    """"
    Create the submission and save the csv file
    """

    # get the PDU object
    # TODO #249 MRB: handle case where PDU does not exist
    pdu = await PaediatricDiabetesUnit.objects.aget(pz_code=pdu_pz_code)

    # Set previous submission to inactive
    if await Submission.objects.filter(
        paediatric_diabetes_unit__pz_code=pdu.pz_code,
        audit_year=audit_year,
        submission_active=True,
    ).aexists():
        original_submission = await Submission.objects.filter(
            submission_active=True,
            paediatric_diabetes_unit__pz_code=pdu.pz_code,
            audit_year=audit_year,
        ).aget()  # there can be only one of these - store it in a variable in case we need to revert
    else:
        original_submission = None

    # Create new submission for the audit year
    # It is not possble to create submissions in years other than the current year
    try:
        new_submission = await Submission.objects.acreate(
            paediatric_diabetes_unit=pdu,
            audit_year=audit_year,
            submission_date=timezone.now(),
            submission_by=user,  # user is the user who is logged in. Passed in as a parameter
            submission_active=True,
            csv_file=csv_file_bytes,
            csv_file_name=csv_file_name,
        )

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
            logger.debug(
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

    """
    Process the csv file and validate and save the data in the tables, parsing any errors
    """

    # Remember the original row number to help users find where the problem was in the CSV
    dataframe = dataframe.assign(row_index=np.arange(dataframe.shape[0]))

    # We only one to create one patient per NHS number (or URN if in Jersey) and we can't create their visits if we fail to save the patient model
    if new_submission.paediatric_diabetes_unit.pz_code == "PZ248":
        visits_by_patient = dataframe.groupby(
            "Unique Reference Number", sort=False, dropna=False
        )
    else:
        visits_by_patient = dataframe.groupby("NHS Number", sort=False, dropna=False)

    # Gather all error messages indexed by row number and the field that caused them (__all__ if we don't know which one)
    # dict[number, dict[str, list[str]]]
    errors_to_return = collections.defaultdict(lambda: collections.defaultdict(list))

    async def process_rows_for_patient(rows, async_client):
        first_row = rows.iloc[0]
        patient_row_index = int(first_row["row_index"])

        transfer_fields = validate_transfer(first_row)

        patient_form = await validate_patient_using_form(first_row, async_client)

        # Pull through cleaned_data so we can use it in the async visit validators
        patient_form.is_valid()

        record_errors_from_form(errors_to_return, patient_row_index, patient_form)

        visit_forms = []
        for _, row in rows.iterrows():
            visit_form = await validate_visit_using_form(
                patient_form, row, async_client
            )
            visit_forms.append((visit_form, int(row["row_index"])))
        
        try:
            retain_errors_and_invalid_field_data(patient_form)

            patient = await sync_to_async(lambda: patient_form.save())()

            if patient:
                # add the patient to a new Transfer instance
                transfer_fields["paediatric_diabetes_unit"] = pdu
                transfer_fields["patient"] = patient
                await Transfer.objects.acreate(**transfer_fields)

                await new_submission.patients.aadd(patient)
        except Exception as error:
            logger.exception(
                f"Error saving patient for {pdu_pz_code} from {csv_file_name}[{patient_row_index}]: {error}"
            )

            # We don't know what field caused the error so add to __all__
            errors_to_return[patient_row_index]["__all__"].append(str(error))

        if patient:
            for visit_form, visit_row_index in visit_forms:
                record_errors_from_form(
                    errors_to_return, visit_row_index, visit_form
                )

                try:
                    retain_errors_and_invalid_field_data(visit_form)
                    visit_form.instance.patient = patient

                    await sync_to_async(lambda: visit_form.save())()
                except Exception as error:
                    logger.exception(
                        f"Error saving visit for {pdu_pz_code} from {csv_file_name}[{visit_row_index}]: {error}"
                    )
                    errors_to_return[visit_row_index]["__all__"].append(str(error))

    async with httpx.AsyncClient() as async_client:
        async with asyncio.TaskGroup() as tg:
            # The maximum number of patients we will process in parallel
            # NB: each patient has a variable number of visits
            #
            # I tried 20, 10, 5 and 3 with 200 patients (16 visits each)
            # 20: 59s.
            # 10: 44s.
            # 5: 42s
            # 3: 45s
            #
            # I also tried no task group at all, just doing each patient in sequence
            # That took 1m 1s.
            #
            # So I went with 5. Seems a reasonable balance between an actual speed up and not hammering third party APIs.
            throttle_semaphore = asyncio.Semaphore(5)

            counter = 1

            for _, rows in visits_by_patient:
                async def task(ix):
                    if(throttle_semaphore.locked()):
                        print(f"!! [PATIENT {ix} waiting to start")

                    async with throttle_semaphore:
                        print(f"!! [PATIENT] {ix} starting")
                        await process_rows_for_patient(rows, async_client)
                        print(f"!! [PATIENT] {ix} complete")
                
                tg.create_task(task(counter))
                counter += 1

    # TODO MRB: why is it saying 1 rows worth of errors? I must have broke the error reporting somehow
    
    # Store the errors to report back to the user in the Data Quality Report
    if errors_to_return:
        new_submission.errors = json.dumps(errors_to_return)
        await new_submission.asave()

    return errors_to_return
