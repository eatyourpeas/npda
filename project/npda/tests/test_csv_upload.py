from functools import partial
from unittest.mock import AsyncMock, patch

from asgiref.sync import sync_to_async

import nhs_number
import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.exceptions import ValidationError
from httpx import HTTPError

from project.npda.general_functions.csv_upload import csv_upload, read_csv
from project.npda.models import NPDAUser, Patient, Visit
from project.npda.tests.factories.patient_factory import (
    INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE, TODAY, VALID_FIELDS)


# We don't want to call remote services in unit tests
@pytest.fixture(autouse=True)
def mock_remote_calls():
    with patch("project.npda.forms.patient_form.validate_postcode", AsyncMock(return_value={"normalised_postcode": VALID_FIELDS["postcode"]})):
        with patch("project.npda.forms.patient_form.gp_ods_code_for_postcode", AsyncMock(return_value = "G85023")):
            with patch("project.npda.forms.patient_form.gp_details_for_ods_code", AsyncMock(return_value = True)):
                with patch("project.npda.models.patient.aimd_for_postcode", AsyncMock(return_value = INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE)):
                    yield None


ALDER_HEY_PZ_CODE = "PZ074"


@pytest.fixture
def dummy_sheets_folder(request):
    return request.config.rootdir / 'project' / 'npda' / 'dummy_sheets'

@pytest.fixture
def valid_df(dummy_sheets_folder):
    return read_csv(dummy_sheets_folder / 'dummy_sheet.csv')

@pytest.fixture
def single_row_valid_df(dummy_sheets_folder):
    df = read_csv(dummy_sheets_folder / 'dummy_sheet.csv').head(1)
    assert(len(df) == 1)

    return df

@pytest.fixture
def one_patient_two_visits(dummy_sheets_folder):
    df = read_csv(dummy_sheets_folder / 'dummy_sheet.csv').head(2)

    assert(len(df) == 2)
    assert(df["NHS Number"][0] == df["NHS Number"][1])

    return df

@pytest.fixture
def two_patients_first_with_two_visits_second_with_one(dummy_sheets_folder):
    df = read_csv(dummy_sheets_folder / 'dummy_sheet.csv').head(3)

    assert(len(df) == 3)
    assert(df["NHS Number"][0] == df["NHS Number"][1])
    assert(df["NHS Number"][2] != df["NHS Number"][0])

    return df

@pytest.fixture
def test_user(seed_groups_fixture, seed_users_fixture):
    return NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()

@sync_to_async
def async_get_all(query_set_fn):
    return list(query_set_fn())


@pytest.mark.django_db
async def test_create_patient(test_user, single_row_valid_df):
    await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)
    patient = await Patient.objects.afirst()

    assert(patient.nhs_number == nhs_number.standardise_format(single_row_valid_df["NHS Number"][0]))
    assert(patient.date_of_birth == single_row_valid_df["Date of Birth"][0].date())
    assert(patient.diabetes_type == single_row_valid_df["Diabetes Type"][0])
    assert(patient.diagnosis_date == single_row_valid_df["Date of Diabetes Diagnosis"][0].date())
    assert(patient.death_date is None)


@pytest.mark.django_db
async def test_create_patient_with_death_date(test_user, single_row_valid_df):
    death_date = VALID_FIELDS["diagnosis_date"] + relativedelta(years=1)
    single_row_valid_df.loc[0, "Death Date"] = pd.to_datetime(death_date)

    await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)
    patient = await Patient.objects.afirst()

    assert(patient.death_date == single_row_valid_df["Death Date"][0].date())


@pytest.mark.django_db
async def test_multiple_patients(test_user, two_patients_first_with_two_visits_second_with_one):
    df = two_patients_first_with_two_visits_second_with_one

    assert(df["NHS Number"][0] == df["NHS Number"][1])
    assert(df["NHS Number"][0] != df["NHS Number"][2])

    await csv_upload(test_user, df, None, ALDER_HEY_PZ_CODE)

    assert(await Patient.objects.acount() == 2)
    [first_patient, second_patient] = await async_get_all(lambda: Patient.objects.all())

    assert(await Visit.objects.filter(patient=first_patient).acount() == 2)
    assert(await Visit.objects.filter(patient=second_patient).acount() == 1)

    assert(first_patient.nhs_number == nhs_number.standardise_format(df["NHS Number"][0]))
    assert(first_patient.date_of_birth == df["Date of Birth"][0].date())
    assert(first_patient.diabetes_type == df["Diabetes Type"][0])
    assert(first_patient.diagnosis_date == df["Date of Diabetes Diagnosis"][0].date())

    assert(second_patient.nhs_number == nhs_number.standardise_format(df["NHS Number"][2]))
    assert(second_patient.date_of_birth == df["Date of Birth"][2].date())
    assert(second_patient.diabetes_type == df["Diabetes Type"][2])
    assert(second_patient.diagnosis_date == df["Date of Diabetes Diagnosis"][2].date())


@pytest.mark.parametrize("column", [
    pytest.param("NHS Number"),
    pytest.param("Date of Birth"),
    pytest.param("Diabetes Type"),
    pytest.param("Date of Diabetes Diagnosis")
])
@pytest.mark.django_db
async def test_missing_mandatory_field(test_user, valid_df, column):
    valid_df.loc[0, column] = None

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, valid_df, None, ALDER_HEY_PZ_CODE)

    # Catastrophic - we can't save this patient at all so we won't save any of the patients in the submission
    assert(await Patient.objects.acount() == 0)


@pytest.mark.django_db
async def test_error_in_single_visit(test_user, single_row_valid_df):
    single_row_valid_df.loc[0, 'Diabetes Treatment at time of Hba1c measurement'] = 45

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    visit = await Visit.objects.afirst()

    assert(visit.treatment == 45)
    assert("treatment" in visit.errors)


@pytest.mark.django_db
async def test_error_in_multiple_visits(test_user, one_patient_two_visits):
    df = one_patient_two_visits
    df.loc[0, 'Diabetes Treatment at time of Hba1c measurement'] = 45

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, df, None, ALDER_HEY_PZ_CODE)

    assert(await Visit.objects.acount() == 2)

    [first_visit, second_visit] = await async_get_all(lambda: Visit.objects.all().order_by('visit_date'))

    assert(first_visit.treatment == 45)
    assert("treatment" in first_visit.errors)

    assert(second_visit.treatment == df["Diabetes Treatment at time of Hba1c measurement"][1])
    assert(second_visit.errors is None)


@pytest.mark.django_db
async def test_multiple_patients_where_one_has_visit_errors_and_the_other_does_not(test_user, two_patients_first_with_two_visits_second_with_one):
    df = two_patients_first_with_two_visits_second_with_one

    assert(df["NHS Number"][0] == df["NHS Number"][1])
    assert(df["NHS Number"][0] != df["NHS Number"][2])

    df.loc[0, 'Diabetes Treatment at time of Hba1c measurement'] = 45

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, df, None, ALDER_HEY_PZ_CODE)

    [patient_one, patient_two] = await async_get_all(lambda: Patient.objects.all())

    assert(await Visit.objects.acount() == 3)

    [first_visit_for_first_patient, second_visit_for_first_patient] = await async_get_all(
        lambda: Visit.objects.filter(patient=patient_one).order_by('visit_date')
    )

    [visit_for_second_patient] = await async_get_all(
        lambda: Visit.objects.filter(patient=patient_two)
    )

    assert(first_visit_for_first_patient.treatment == 45)
    assert("treatment" in first_visit_for_first_patient.errors)

    assert(second_visit_for_first_patient.treatment == df["Diabetes Treatment at time of Hba1c measurement"][1])
    assert(second_visit_for_first_patient.errors is None)

    assert(visit_for_second_patient.treatment == df["Diabetes Treatment at time of Hba1c measurement"][2])
    assert(visit_for_second_patient.errors is None)


@pytest.mark.django_db
async def test_multiple_patients_with_visit_errors():
    # TODO MRB: implement this test
    pass


@pytest.mark.django_db
async def test_invalid_nhs_number(test_user, single_row_valid_df):
    invalid_nhs_number = "123456789"
    single_row_valid_df["NHS Number"] = invalid_nhs_number

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    # Not catastrophic - error saved in model and raised back to caller
    patient = await Patient.objects.afirst()

    assert(patient.nhs_number == invalid_nhs_number)

    # TODO MRB: create a ValidationError model field
    assert("nhs_number" in patient.errors)


@pytest.mark.django_db
async def test_future_date_of_birth(test_user, single_row_valid_df):
    date_of_birth = TODAY + relativedelta(days=1)
    single_row_valid_df["Date of Birth"] = pd.to_datetime(date_of_birth)

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.date_of_birth == date_of_birth)
    assert("date_of_birth" in patient.errors)

    error_message = patient.errors["date_of_birth"][0]['message']
    assert(error_message == "Cannot be in the future")


@pytest.mark.django_db
async def test_over_25(test_user, single_row_valid_df):
    date_of_birth = TODAY + - relativedelta(years=25, days=1)
    single_row_valid_df["Date of Birth"] = pd.to_datetime(date_of_birth)

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.date_of_birth == date_of_birth)
    assert("date_of_birth" in patient.errors)

    error_message = patient.errors["date_of_birth"][0]['message']
    assert(error_message == "NPDA patients cannot be 25+ years old. This patient is 25")


@pytest.mark.django_db
async def test_invalid_diabetes_type(test_user, single_row_valid_df):
    single_row_valid_df["Diabetes Type"] = 45

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.diabetes_type == 45)
    assert("diabetes_type" in patient.errors)


@pytest.mark.django_db
async def test_future_diagnosis_date(test_user, single_row_valid_df):
    diagnosis_date = TODAY + relativedelta(days=1)
    single_row_valid_df["Date of Diabetes Diagnosis"] = pd.to_datetime(diagnosis_date)

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.diagnosis_date == diagnosis_date)
    assert("diagnosis_date" in patient.errors)

    error_message = patient.errors["diagnosis_date"][0]['message']
    assert(error_message == "Cannot be in the future")


@pytest.mark.django_db
async def test_diagnosis_date_before_date_of_birth(test_user, single_row_valid_df):
    date_of_birth = VALID_FIELDS["date_of_birth"],
    diagnosis_date = VALID_FIELDS["date_of_birth"] - relativedelta(years=1)

    single_row_valid_df["Date of Diabetes Diagnosis"] = pd.to_datetime(diagnosis_date)

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.diagnosis_date == diagnosis_date)
    assert("diagnosis_date" in patient.errors)

    error_message = patient.errors["diagnosis_date"][0]['message']
    # TODO MRB: why does this have entity encoding issues?
    assert(error_message == "&#x27;Date of Diabetes Diagnosis&#x27; cannot be before &#x27;Date of Birth&#x27;")


@pytest.mark.django_db
async def test_invalid_sex(test_user, single_row_valid_df):
    single_row_valid_df["Stated gender"] = 45

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.sex == 45)
    assert("sex" in patient.errors)


@pytest.mark.django_db
async def test_invalid_ethnicity(test_user, single_row_valid_df):
    single_row_valid_df["Ethnic Category"] = "45"

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.ethnicity == "45")
    assert("ethnicity" in patient.errors)


@pytest.mark.django_db
async def test_missing_gp_ods_code(test_user, single_row_valid_df):
    single_row_valid_df["GP Practice Code"] = None

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert("gp_practice_ods_code" in patient.errors)

    error_message = patient.errors["gp_practice_ods_code"][0]['message']
    # TODO MRB: why does this have entity encoding issues?
    assert(error_message == "&#x27;GP Practice ODS code&#x27; and &#x27;GP Practice postcode&#x27; cannot both be empty")



@pytest.mark.django_db
async def test_future_death_date(test_user, single_row_valid_df):
    death_date = TODAY + relativedelta(days = 1)

    single_row_valid_df["Death Date"] = pd.to_datetime(death_date)

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.death_date == death_date)
    assert("death_date" in patient.errors)

    error_message = patient.errors["death_date"][0]['message']
    assert(error_message == "Cannot be in the future")


@pytest.mark.django_db
async def test_death_date_before_date_of_birth(test_user, single_row_valid_df):
    date_of_birth = VALID_FIELDS["date_of_birth"],
    death_date = VALID_FIELDS["date_of_birth"] - relativedelta(years=1)

    single_row_valid_df["Death Date"] = pd.to_datetime(death_date)

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.death_date == death_date)
    assert("death_date" in patient.errors)

    error_message = patient.errors["death_date"][0]['message']
    # TODO MRB: why does this have entity encoding issues?
    assert(error_message == "&#x27;Death Date&#x27; cannot be before &#x27;Date of Birth&#x27;")


@pytest.mark.django_db
@patch("project.npda.forms.patient_form.validate_postcode", AsyncMock(return_value=None))
async def test_invalid_postcode(test_user, single_row_valid_df):
    single_row_valid_df["Postcode of usual address"] = "not a postcode"

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.postcode == "not a postcode")
    assert("postcode" in patient.errors)


@pytest.mark.django_db
@patch("project.npda.forms.patient_form.validate_postcode", AsyncMock(side_effect=HTTPError("oopsie!")))
async def test_error_validating_postcode(test_user, single_row_valid_df):
    single_row_valid_df["Postcode of usual address"] = "WC1X 8SH"

    await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()
    assert(patient.postcode == "WC1X8SH")


@pytest.mark.django_db
@patch("project.npda.forms.patient_form.gp_details_for_ods_code", AsyncMock(return_value=None))
async def test_invalid_gp_ods_code(test_user, single_row_valid_df):
    single_row_valid_df["GP Practice Code"] = "not a GP code"

    with pytest.raises(ValidationError) as e_info:
        await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()

    assert(patient.gp_practice_ods_code == "not a GP code")
    assert("gp_practice_ods_code" in patient.errors)


@pytest.mark.django_db
@patch("project.npda.forms.patient_form.gp_details_for_ods_code", AsyncMock(side_effect=HTTPError("oopsie!")))
async def test_error_validating_gp_ods_code(test_user, single_row_valid_df):
    single_row_valid_df["GP Practice Code"] = "G85023"

    await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()
    assert(patient.gp_practice_ods_code == "G85023")


@pytest.mark.django_db
async def test_lookup_index_of_multiple_deprivation(test_user, single_row_valid_df):
    await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()
    assert(patient.index_of_multiple_deprivation_quintile == INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE)


@pytest.mark.django_db
@patch("project.npda.models.patient.imd_for_postcode", AsyncMock(side_effect=HTTPError("oopsie!")))
async def test_error_looking_up_index_of_multiple_deprivation(test_user, single_row_valid_df):
    await csv_upload(test_user, single_row_valid_df, None, ALDER_HEY_PZ_CODE)

    patient = await Patient.objects.afirst()
    assert(patient.index_of_multiple_deprivation_quintile is None)
