import dataclasses
import datetime
import tempfile
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync

import nhs_number
import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point
from httpx import HTTPError

from project.npda.general_functions.csv import csv_upload, csv_parse
from project.constants import ALL_DATES
from project.npda.models import NPDAUser, Patient, Visit
from project.npda.tests.factories.patient_factory import (
    INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE,
    TODAY,
    VALID_FIELDS,
    LOCATION,
)
from project.npda.forms.external_patient_validators import (
    PatientExternalValidationResult,
)
from project.npda.forms.external_visit_validators import (
    VisitExternalValidationResult,
    CentileAndSDS,
)


MOCK_PATIENT_EXTERNAL_VALIDATION_RESULT = PatientExternalValidationResult(
    postcode=VALID_FIELDS["postcode"],
    gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
    gp_practice_postcode=None,
    index_of_multiple_deprivation_quintile=INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE,
    location_bng=Point(100, -100),
    location_wgs84=Point(200, -200),
)

MOCK_VISIT_EXTERNAL_VALIDATION_RESULT = VisitExternalValidationResult(
    height_result=CentileAndSDS(centile=Decimal(0.5), sds=Decimal(0.5)),
    weight_result=CentileAndSDS(centile=Decimal(0.5), sds=Decimal(0.5)),
    bmi=Decimal(0.5),
    bmi_result=CentileAndSDS(centile=Decimal(0.5), sds=Decimal(0.5)),
)


def mock_patient_external_validation_result(**kwargs):
    return AsyncMock(
        return_value=dataclasses.replace(
            MOCK_PATIENT_EXTERNAL_VALIDATION_RESULT, **kwargs
        )
    )


# We don't want to call remote services in unit tests
@pytest.fixture(autouse=True)
def mock_remote_calls():
    with patch(
        "project.npda.general_functions.csv.csv_upload.validate_patient_async",
        AsyncMock(return_value=MOCK_PATIENT_EXTERNAL_VALIDATION_RESULT),
    ):
        with patch(
            "project.npda.general_functions.csv.csv_upload.validate_visit_async",
            AsyncMock(return_value=MOCK_VISIT_EXTERNAL_VALIDATION_RESULT),
        ):
            yield None


ALDER_HEY_PZ_CODE = "PZ074"


@pytest.fixture
def valid_df(dummy_sheets_folder):
    file = dummy_sheets_folder / "dummy_sheet.csv"
    return csv_parse(file).df


@pytest.fixture
def single_row_valid_df(dummy_sheets_folder):
    file = dummy_sheets_folder / "dummy_sheet.csv"
    df = csv_parse(file).df
    df = df.head(1)

    return df


@pytest.fixture
def one_patient_two_visits(dummy_sheets_folder):
    file = dummy_sheets_folder / "dummy_sheet.csv"
    df = csv_parse(file).df

    df = df.head(2)
    assert df["NHS Number"][0] == df["NHS Number"][1]

    return df


@pytest.fixture
def two_patients_first_with_two_visits_second_with_one(dummy_sheets_folder):
    file = dummy_sheets_folder / "dummy_sheet.csv"
    df = csv_parse(file).df

    df = df.head(3)

    assert df["NHS Number"][0] == df["NHS Number"][1]
    assert df["NHS Number"][2] != df["NHS Number"][0]

    return df


@pytest.fixture
def two_patients_with_one_visit_each(dummy_sheets_folder):
    file = dummy_sheets_folder / "dummy_sheet.csv"
    df = csv_parse(file).df

    df = df.drop([0]).head(2).reset_index(drop=True)

    assert len(df) == 2
    assert df["NHS Number"][1] != df["NHS Number"][0]

    return df


@pytest.fixture
def test_user(seed_groups_fixture, seed_users_fixture):
    return NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()


# The database is not rolled back if we used the built in async support for pytest
# https://github.com/pytest-dev/pytest-asyncio/issues/226
@async_to_sync
async def csv_upload_sync(user, dataframe):
    return await csv_upload(
        user,
        dataframe,
        csv_file_name=None,
        csv_file_bytes=None,
        pdu_pz_code=ALDER_HEY_PZ_CODE,
        audit_year=2024,
    )


def read_csv_from_str(contents):
    with tempfile.NamedTemporaryFile() as f:
        f.write(contents.encode())
        f.seek(0)

        return csv_parse(f)


@pytest.mark.django_db
def test_create_patient(test_user, single_row_valid_df):

    csv_upload_sync(test_user, single_row_valid_df)
    patient = Patient.objects.first()

    assert patient.nhs_number == nhs_number.standardise_format(
        single_row_valid_df["NHS Number"][0]
    )
    assert patient.date_of_birth == single_row_valid_df["Date of Birth"][0].date()
    assert patient.diabetes_type == single_row_valid_df["Diabetes Type"][0]
    assert (
        patient.diagnosis_date
        == single_row_valid_df["Date of Diabetes Diagnosis"][0].date()
    )
    assert patient.death_date is None


@pytest.mark.django_db
def test_create_patient_with_death_date(test_user, single_row_valid_df):
    death_date = VALID_FIELDS["diagnosis_date"] + relativedelta(years=1)
    single_row_valid_df.loc[0, "Death Date"] = pd.to_datetime(death_date)

    csv_upload_sync(test_user, single_row_valid_df)
    patient = Patient.objects.first()

    assert patient.death_date == single_row_valid_df["Death Date"][0].date()


@pytest.mark.django_db
def test_multiple_patients(
    test_user, two_patients_first_with_two_visits_second_with_one
):
    df = two_patients_first_with_two_visits_second_with_one

    assert df["NHS Number"][0] == df["NHS Number"][1]
    assert df["NHS Number"][0] != df["NHS Number"][2]

    csv_upload_sync(test_user, df)

    assert Patient.objects.count() == 2
    [first_patient, second_patient] = Patient.objects.all()

    assert Visit.objects.filter(patient=first_patient).count() == 2
    assert Visit.objects.filter(patient=second_patient).count() == 1

    assert first_patient.nhs_number == nhs_number.standardise_format(
        df["NHS Number"][0]
    )
    assert first_patient.date_of_birth == df["Date of Birth"][0].date()
    assert first_patient.diabetes_type == df["Diabetes Type"][0]
    assert first_patient.diagnosis_date == df["Date of Diabetes Diagnosis"][0].date()

    assert second_patient.nhs_number == nhs_number.standardise_format(
        df["NHS Number"][2]
    )
    assert second_patient.date_of_birth == df["Date of Birth"][2].date()
    assert second_patient.diabetes_type == df["Diabetes Type"][2]
    assert second_patient.diagnosis_date == df["Date of Diabetes Diagnosis"][2].date()


@pytest.mark.parametrize(
    "column,model_field",
    [
        pytest.param("NHS Number", "nhs_number"),
        pytest.param("Date of Birth", "date_of_birth"),
        pytest.param("Diabetes Type", "diabetes_type"),
        pytest.param("Date of Diabetes Diagnosis", "diagnosis_date"),
    ],
)
@pytest.mark.django_db(transaction=True)
def test_missing_mandatory_field(
    seed_groups_per_function_fixture,
    seed_users_per_function_fixture,
    single_row_valid_df,
    column,
    model_field,
):
    # As these tests need full transaction support we can't use our session fixtures
    test_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()

    # Delete all patients to ensure we're starting from a clean slate
    Patient.objects.all().delete()

    single_row_valid_df.loc[0, column] = None

    assert (
        Patient.objects.count() == 0
    ), "There should be no patients in the database before the test"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert model_field in errors[0]

    # Catastrophic - we can't save this patient at all so we won't save any of the patients in the submission
    assert Patient.objects.count() == 0


@pytest.mark.django_db
def test_error_in_single_visit(test_user, single_row_valid_df):
    single_row_valid_df.loc[0, "Diabetes Treatment at time of Hba1c measurement"] = 45
    single_row_valid_df.loc[
        0,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 3

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "treatment" in errors[0]

    visit = Visit.objects.first()

    assert visit.treatment == 45
    assert "treatment" in visit.errors


@pytest.mark.django_db
def test_error_in_multiple_visits(test_user, one_patient_two_visits):
    df = one_patient_two_visits
    df.loc[0, "Diabetes Treatment at time of Hba1c measurement"] = 45
    df.loc[
        0,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 3
    df.loc[1, "Diabetes Treatment at time of Hba1c measurement"] = 3
    df.loc[
        1,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 3

    errors = csv_upload_sync(test_user, df)
    assert "treatment" in errors[0]

    assert Visit.objects.count() == 2

    [first_visit, second_visit] = Visit.objects.all().order_by("visit_date")

    print(second_visit.patient.nhs_number)

    assert first_visit.treatment == 45
    assert "treatment" in first_visit.errors

    assert (
        second_visit.treatment
        == df["Diabetes Treatment at time of Hba1c measurement"][1]
    )

    assert second_visit.errors is None


@pytest.mark.django_db
def test_multiple_patients_where_one_has_visit_errors_and_the_other_does_not(
    test_user, two_patients_first_with_two_visits_second_with_one
):
    df = two_patients_first_with_two_visits_second_with_one

    assert df["NHS Number"][0] == df["NHS Number"][1]
    assert df["NHS Number"][0] != df["NHS Number"][2]

    df.loc[0, "Diabetes Treatment at time of Hba1c measurement"] = 45
    df.loc[
        0,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 3

    errors = csv_upload_sync(test_user, df)
    assert "treatment" in errors[0]

    [patient_one, patient_two] = Patient.objects.all()

    assert Visit.objects.count() == 3

    [first_visit_for_first_patient, second_visit_for_first_patient] = (
        Visit.objects.filter(patient=patient_one).order_by("visit_date")
    )

    [visit_for_second_patient] = Visit.objects.filter(patient=patient_two)

    assert first_visit_for_first_patient.treatment == 45
    assert "treatment" in first_visit_for_first_patient.errors

    assert (
        second_visit_for_first_patient.treatment
        == df["Diabetes Treatment at time of Hba1c measurement"][1]
    )
    assert second_visit_for_first_patient.errors is None

    assert (
        visit_for_second_patient.treatment
        == df["Diabetes Treatment at time of Hba1c measurement"][2]
    )
    assert visit_for_second_patient.errors is None


@pytest.mark.django_db
def test_multiple_patients_with_visit_errors(
    test_user, two_patients_with_one_visit_each
):
    df = two_patients_with_one_visit_each

    df.loc[0, "Diabetes Treatment at time of Hba1c measurement"] = 45
    df.loc[
        0,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 3
    df.loc[1, "Diabetes Treatment at time of Hba1c measurement"] = 45
    df.loc[
        1,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 3

    errors = csv_upload_sync(test_user, df)

    assert "treatment" in errors[0]
    assert "treatment" in errors[1]

    [patient_one, patient_two] = Patient.objects.all()

    assert Visit.objects.count() == 2

    visit_for_first_patient = Visit.objects.filter(patient=patient_one).first()
    visit_for_second_patient = Visit.objects.filter(patient=patient_two).first()

    assert visit_for_first_patient.treatment == 45
    assert "treatment" in visit_for_first_patient.errors

    assert visit_for_second_patient.treatment == 45
    assert "treatment" in visit_for_second_patient.errors


@pytest.mark.django_db
def test_invalid_nhs_number(test_user, single_row_valid_df):
    invalid_nhs_number = "123456789"
    single_row_valid_df["NHS Number"] = invalid_nhs_number

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "nhs_number" in errors[0]

    # Catastrophic - Patient not save
    assert Patient.objects.count() == 0

    # TODO MRB: create a ValidationError model field (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/332)


@pytest.mark.django_db
def test_future_date_of_birth(test_user, single_row_valid_df):
    date_of_birth = TODAY + relativedelta(days=1)
    single_row_valid_df["Date of Birth"] = pd.to_datetime(date_of_birth)

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "date_of_birth" in errors[0]

    patient = Patient.objects.first()

    assert patient.date_of_birth == date_of_birth
    assert "date_of_birth" in patient.errors

    error_message = patient.errors["date_of_birth"][0]["message"]
    assert error_message == "Cannot be in the future"


@pytest.mark.django_db
def test_over_25(test_user, single_row_valid_df):
    date_of_birth = TODAY + -relativedelta(years=25, days=1)
    single_row_valid_df["Date of Birth"] = pd.to_datetime(date_of_birth)

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "date_of_birth" in errors[0]

    patient = Patient.objects.first()

    assert patient.date_of_birth == date_of_birth
    assert "date_of_birth" in patient.errors

    error_message = patient.errors["date_of_birth"][0]["message"]
    assert error_message == "NPDA patients cannot be 25+ years old. This patient is 25"


@pytest.mark.django_db
def test_invalid_diabetes_type(test_user, single_row_valid_df):
    single_row_valid_df["Diabetes Type"] = 45

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "diabetes_type" in errors[0]

    patient = Patient.objects.first()

    assert patient.diabetes_type == 45
    assert "diabetes_type" in patient.errors


@pytest.mark.django_db
def test_future_diagnosis_date(test_user, single_row_valid_df):
    diagnosis_date = TODAY + relativedelta(days=1)
    single_row_valid_df["Date of Diabetes Diagnosis"] = pd.to_datetime(diagnosis_date)

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "diagnosis_date" in errors[0]

    patient = Patient.objects.first()

    assert patient.diagnosis_date == diagnosis_date
    assert "diagnosis_date" in patient.errors

    error_message = patient.errors["diagnosis_date"][0]["message"]
    assert error_message == "Cannot be in the future"


@pytest.mark.django_db
def test_diagnosis_date_before_date_of_birth(test_user, single_row_valid_df):
    date_of_birth = (VALID_FIELDS["date_of_birth"],)
    diagnosis_date = VALID_FIELDS["date_of_birth"] - relativedelta(years=1)

    single_row_valid_df["Date of Diabetes Diagnosis"] = pd.to_datetime(diagnosis_date)

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "diagnosis_date" in errors[0]

    patient = Patient.objects.first()

    assert patient.diagnosis_date == diagnosis_date
    assert "diagnosis_date" in patient.errors

    error_message = patient.errors["diagnosis_date"][0]["message"]
    # TODO MRB: why does this have entity encoding issues? (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/333)
    assert (
        error_message
        == "&#x27;Date of Diabetes Diagnosis&#x27; cannot be before &#x27;Date of Birth&#x27;"
    )


@pytest.mark.django_db
def test_invalid_sex(test_user, single_row_valid_df):
    single_row_valid_df["Stated gender"] = 45

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "sex" in errors[0]

    patient = Patient.objects.first()

    assert patient.sex == 45
    assert "sex" in patient.errors


@pytest.mark.django_db
def test_invalid_ethnicity(test_user, single_row_valid_df):
    single_row_valid_df["Ethnic Category"] = "45"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "ethnicity" in errors[0]

    patient = Patient.objects.first()

    assert patient.ethnicity == "45"
    assert "ethnicity" in patient.errors


@pytest.mark.django_db
def test_missing_gp_ods_code(test_user, single_row_valid_df):
    single_row_valid_df["GP Practice Code"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "gp_practice_ods_code" in errors[0]

    patient = Patient.objects.first()

    assert "gp_practice_ods_code" in patient.errors

    error_message = patient.errors["gp_practice_ods_code"][0]["message"]
    # TODO MRB: why does this have entity encoding issues? (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/333)
    assert (
        error_message
        == "&#x27;GP Practice ODS code&#x27; and &#x27;GP Practice postcode&#x27; cannot both be empty"
    )


@pytest.mark.django_db
def test_future_death_date(test_user, single_row_valid_df):
    death_date = TODAY + relativedelta(days=1)

    single_row_valid_df["Death Date"] = pd.to_datetime(death_date)

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "death_date" in errors[0]

    patient = Patient.objects.first()

    assert patient.death_date == death_date
    assert "death_date" in patient.errors

    error_message = patient.errors["death_date"][0]["message"]
    assert error_message == "Cannot be in the future"


@pytest.mark.django_db
def test_death_date_before_date_of_birth(test_user, single_row_valid_df):
    date_of_birth = (VALID_FIELDS["date_of_birth"],)
    death_date = VALID_FIELDS["date_of_birth"] - relativedelta(years=1)

    single_row_valid_df["Death Date"] = pd.to_datetime(death_date)

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "death_date" in errors[0]

    patient = Patient.objects.first()

    assert patient.death_date == death_date
    assert "death_date" in patient.errors

    error_message = patient.errors["death_date"][0]["message"]
    # TODO MRB: why does this have entity encoding issues? (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/333)
    assert (
        error_message
        == "&#x27;Death Date&#x27; cannot be before &#x27;Date of Birth&#x27;"
    )


@pytest.mark.django_db
@patch(
    "project.npda.general_functions.csv.csv_upload.validate_patient_async",
    mock_patient_external_validation_result(
        postcode=ValidationError("Invalid postcode")
    ),
)
def test_invalid_postcode(test_user, single_row_valid_df):
    single_row_valid_df["Postcode of usual address"] = "not a postcode"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "postcode" in errors[0]

    patient = Patient.objects.first()

    assert patient.postcode == "not a postcode"
    assert "postcode" in patient.errors


@pytest.mark.django_db
@patch(
    "project.npda.general_functions.csv.csv_upload.validate_patient_async",
    mock_patient_external_validation_result(postcode=None),
)
def test_error_validating_postcode(test_user, single_row_valid_df):
    single_row_valid_df["Postcode of usual address"] = "WC1X 8SH"
    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    patient = Patient.objects.first()
    assert patient.postcode == "WC1X8SH"


@pytest.mark.django_db
@patch(
    "project.npda.general_functions.csv.csv_upload.validate_patient_async",
    mock_patient_external_validation_result(
        gp_practice_ods_code=ValidationError("Invalid ODS code")
    ),
)
def test_invalid_gp_ods_code(test_user, single_row_valid_df):
    single_row_valid_df["GP Practice Code"] = "not a GP code"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "gp_practice_ods_code" in errors[0]

    patient = Patient.objects.first()

    assert patient.gp_practice_ods_code == "not a GP code"
    assert "gp_practice_ods_code" in patient.errors


@pytest.mark.django_db
@patch(
    "project.npda.general_functions.csv.csv_upload.validate_patient_async",
    mock_patient_external_validation_result(postcode=None),
)
def test_error_validating_gp_ods_code(test_user, single_row_valid_df):
    single_row_valid_df["GP Practice Code"] = "G85023"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert len(errors) == 0

    patient = Patient.objects.first()
    assert patient.gp_practice_ods_code == "G85023"


@pytest.mark.django_db
def test_lookup_index_of_multiple_deprivation(test_user, single_row_valid_df):
    csv_upload_sync(test_user, single_row_valid_df)

    patient = Patient.objects.first()
    assert (
        patient.index_of_multiple_deprivation_quintile
        == INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE
    )


@pytest.mark.django_db
@patch(
    "project.npda.general_functions.csv.csv_upload.validate_patient_async",
    mock_patient_external_validation_result(
        index_of_multiple_deprivation_quintile=None
    ),
)
def test_error_looking_up_index_of_multiple_deprivation(test_user, single_row_valid_df):
    csv_upload_sync(test_user, single_row_valid_df)

    patient = Patient.objects.first()
    assert patient.index_of_multiple_deprivation_quintile is None


@pytest.mark.django_db
def test_save_location_from_postcode(test_user, single_row_valid_df):
    csv_upload_sync(test_user, single_row_valid_df)

    patient = Patient.objects.first()
    assert patient.location_bng == MOCK_PATIENT_EXTERNAL_VALIDATION_RESULT.location_bng
    assert (
        patient.location_wgs84 == MOCK_PATIENT_EXTERNAL_VALIDATION_RESULT.location_wgs84
    )


@pytest.mark.django_db
@patch(
    "project.npda.general_functions.csv.csv_upload.validate_patient_async",
    mock_patient_external_validation_result(
        location_bng=None,
        location_wgs84=None,
    ),
)
def test_missing_location_from_postcode(test_user, single_row_valid_df):
    csv_upload_sync(test_user, single_row_valid_df)

    patient = Patient.objects.first()
    assert patient.location_bng is None
    assert patient.location_wgs84 is None


@pytest.mark.django_db
def test_strip_first_spaces_in_column_name(test_user, dummy_sheet_csv):
    csv = dummy_sheet_csv.replace("NHS Number", "  NHS Number")
    df = read_csv_from_str(csv).df

    assert df.columns[0] == "NHS Number"

    csv_upload_sync(test_user, df)
    patient = Patient.objects.first()

    assert patient.nhs_number == nhs_number.standardise_format(df["NHS Number"][0])


@pytest.mark.django_db
def test_strip_last_spaces_in_column_name(test_user, dummy_sheet_csv):
    csv = dummy_sheet_csv.replace("NHS Number", "NHS Number  ")
    df = read_csv_from_str(csv).df

    assert df.columns[0] == "NHS Number"

    csv_upload_sync(test_user, df)
    patient = Patient.objects.first()

    assert patient.nhs_number == nhs_number.standardise_format(df["NHS Number"][0])


# Originally found in https://github.com/rcpch/national-paediatric-diabetes-audit/actions/runs/11627684066/job/32381466250
# so we have a separate unit test for it
@pytest.mark.django_db
def test_spaces_in_date_column_name(test_user, dummy_sheet_csv):
    csv = dummy_sheet_csv.replace("Date of Birth", "  Date of Birth")
    df = read_csv_from_str(csv).df

    csv_upload_sync(test_user, df)
    patient = Patient.objects.first()

    assert patient.date_of_birth == df["Date of Birth"][0].date()


@pytest.mark.django_db
def test_different_column_order(test_user, single_row_valid_df):
    columns = single_row_valid_df.columns.to_list()

    # Move the first column to the end
    columns = columns[1:] + columns[:1]
    df = single_row_valid_df[columns]

    csv_upload_sync(test_user, df)
    assert Patient.objects.count() == 1


# TODO MRB: these should probably be calling the route directly? https://github.com/rcpch/national-paediatric-diabetes-audit/issues/353
@pytest.mark.django_db
def test_additional_columns_causes_error(test_user, single_row_valid_df):
    single_row_valid_df["extra_one"] = "woo"
    single_row_valid_df["extra_two"] = "bloo"

    csv = single_row_valid_df.to_csv(index=False, date_format="%d/%m/%Y")

    additional_columns = read_csv_from_str(csv).additional_columns
    assert additional_columns == ["extra_one", "extra_two"]


@pytest.mark.django_db
def test_duplicate_columns_causes_error(test_user, single_row_valid_df):
    single_row_valid_df["NHS Number_2"] = single_row_valid_df["NHS Number"]
    single_row_valid_df["NHS Number_3"] = single_row_valid_df["NHS Number"]
    single_row_valid_df["Date of Birth_2"] = single_row_valid_df["Date of Birth"]

    csv = single_row_valid_df.to_csv(index=False, date_format="%d/%m/%Y")
    csv = csv.replace("NHS Number_2", "NHS Number")
    csv = csv.replace("NHS Number_3", "NHS Number")
    csv = csv.replace("Date of Birth_2", "Date of Birth")

    duplicate_columns = read_csv_from_str(csv).duplicate_columns
    assert duplicate_columns == ["NHS Number", "Date of Birth"]


@pytest.mark.django_db
def test_missing_columns_causes_error(test_user, single_row_valid_df):
    df = single_row_valid_df.drop(
        columns=["Urinary Albumin Level (ACR)", "Total Cholesterol Level (mmol/l)"]
    )
    csv = df.to_csv(index=False, date_format="%d/%m/%Y")

    missing_columns = read_csv_from_str(csv).missing_columns
    assert missing_columns == [
        "Urinary Albumin Level (ACR)",
        "Total Cholesterol Level (mmol/l)",
    ]


@pytest.mark.django_db
def test_case_insensitive_column_headers(test_user, dummy_sheet_csv):
    csv = dummy_sheet_csv

    lines = csv.split("\n")
    lines[0] = lines[0].lower()
    csv = "\n".join(lines)

    df = read_csv_from_str(csv).df

    errors = csv_upload_sync(test_user, df)

    assert len(errors) == 0  #


@pytest.mark.django_db
def test_mixed_case_column_headers(test_user, dummy_sheet_csv):
    csv = dummy_sheet_csv.replace("NHS Number", "NHS number")
    df = read_csv_from_str(csv).df

    assert df.columns[0] == "NHS Number"


@pytest.mark.django_db
def test_first_row_with_extra_cell_at_the_start(test_user, single_row_valid_df):
    csv = single_row_valid_df.to_csv(index=False, date_format="%d/%m/%Y")

    lines = csv.split("\n")
    lines[1] = "extra_value," + lines[1]

    csv = "\n".join(lines)

    with pytest.raises(ValueError):
        read_csv_from_str(csv)


@pytest.mark.django_db
def test_first_row_with_extra_cell_on_the_end(test_user, single_row_valid_df):
    csv = single_row_valid_df.to_csv(index=False, date_format="%d/%m/%Y")

    lines = csv.split("\n")
    lines[1] += ",extra_value"

    csv = "\n".join(lines)

    with pytest.raises(ValueError):
        read_csv_from_str(csv)


@pytest.mark.django_db
def test_second_row_with_extra_cell_at_the_start(test_user, one_patient_two_visits):
    csv = one_patient_two_visits.to_csv(index=False, date_format="%d/%m/%Y")

    lines = csv.split("\n")
    lines[2] = "extra_value," + lines[1]

    csv = "\n".join(lines)

    with pytest.raises(pd.errors.ParserError):
        read_csv_from_str(csv)


@pytest.mark.django_db
def test_second_row_with_extra_cell_on_the_end(test_user, one_patient_two_visits):
    csv = one_patient_two_visits.to_csv(index=False, date_format="%d/%m/%Y")

    lines = csv.split("\n")
    lines[2] += ",extra_value"

    csv = "\n".join(lines)

    with pytest.raises(pd.errors.ParserError):
        read_csv_from_str(csv)


@pytest.mark.django_db
def test_upload_without_headers(test_user, one_patient_two_visits):
    csv = one_patient_two_visits.to_csv(index=False, date_format="%d/%m/%Y")

    lines = csv.split("\n")
    lines = lines[1:]

    csv = "\n".join(lines)

    # The first row of the csv file does not match any of the predefined column names - this is a fatal error and the csv should be rejected and the user notified
    with pytest.raises(
        ValueError,
        match="The first row of the csv file does not match any of the predefined column names. Please include these and upload the file again.",
    ):
        df = read_csv_from_str(csv).df
        csv_upload_sync(test_user, df)

    # No patients or associated visits should be saved
    assert Patient.objects.count() == 0
    assert Visit.objects.count() == 0


@pytest.mark.django_db
def test_dates_with_short_year(one_patient_two_visits):
    csv = one_patient_two_visits.to_csv(index=False, date_format="%d/%m/%y")
    df = read_csv_from_str(csv).df

    assert(df.equals(one_patient_two_visits))


@pytest.mark.parametrize(
    "column",
    [
        pytest.param("Date of Birth"),
        pytest.param("Date of Diabetes Diagnosis"),
    ],
)
@pytest.mark.django_db(transaction=True)
def test_bad_date_format_on_mandatory_column(
    seed_groups_per_function_fixture,
    seed_users_per_function_fixture,
    one_patient_two_visits,
    column
):
    # As these tests need full transaction support we can't use our session fixtures
    test_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()

    # Delete all patients to ensure we're starting from a clean slate
    Patient.objects.all().delete()

    df = one_patient_two_visits
    
    df[column] = df[column].astype(str)
    df[column] = "beep"

    csv = df.to_csv(index=False, date_format="%d/%m/%Y")

    assert (
        Patient.objects.count() == 0
    ), "There should be no patients in the database before the test"

    df = read_csv_from_str(csv).df
    errors = csv_upload_sync(test_user, df)

    assert(len(errors) == 1)

    assert (
        Patient.objects.count() == 0
    ), "There should be no patients in the database after the test"


@pytest.mark.django_db
def test_bad_date_format_on_optional_column(one_patient_two_visits):
    df = one_patient_two_visits

    column = "Date of Level 3 carbohydrate counting education received"
    
    df[column] = df[column].astype(str)
    df[column] = "beep"

    csv = df.to_csv(index=False, date_format="%d/%m/%Y")
    
    df = read_csv_from_str(csv).df
    assert(len(df) == 2)


@pytest.mark.django_db
def test_upload_csv_with_bool_values_instead_of_int(test_user, single_row_valid_df):
    single_row_valid_df["Has the patient been recommended a Gluten-free diet?"] = True

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "gluten_free_diet" in errors[0]

    visit = Visit.objects.first()
    assert visit.gluten_free_diet == 1


@pytest.mark.django_db
def test_height_is_rounded_to_one_decimal(test_user, single_row_valid_df):
    single_row_valid_df["Patient Height (cm)"] = 123.456
    single_row_valid_df["Patient Weight (kg)"] = 7.89

    csv_upload_sync(test_user, single_row_valid_df)

    visit = Visit.objects.first()

    assert visit.height == round(
        Decimal("123.456"), 1
    )  # Values are stored as Decimals (4 digits with 1 decimal place)
    assert visit.weight == round(
        Decimal("7.89"), 1
    )  # Values are stored as Decimals (4 digits with 1 decimal place)


@pytest.mark.django_db
@patch(
    "project.npda.general_functions.csv.csv_upload.validate_patient_async",
    mock_patient_external_validation_result(
        postcode=ValidationError("Invalid postcode")
    ),
)
def test_cleaned_fields_are_stored_when_other_fields_are_invalid(
    test_user, single_row_valid_df
):
    # PATIENT
    # - Valid, cleaning should remove the spaces
    single_row_valid_df["NHS Number"] = "719 573 0220"

    # Postcode marked as invalid by the mock patched above
    single_row_valid_df["Postcode of usual address"] = "not a real postcode"

    # VISIT
    # - Valid, cleaning should retain only one decimal place
    single_row_valid_df["Patient Weight (kg)"] = 7.89

    # - Invalid - cannot be less than 40
    single_row_valid_df["Patient Height (cm)"] = 38

    csv_upload_sync(test_user, single_row_valid_df)

    patient = Patient.objects.first()
    visit = Visit.objects.first()

    assert patient.nhs_number == "7195730220"  # cleaned version saved
    assert patient.postcode == "not a real postcode"  # saved but invalid

    assert visit.weight == round(Decimal("7.89"), 1)  # cleaned version saved
    assert visit.height == 38  # saved but invalid


@pytest.mark.django_db
def test_async_visit_fields_are_saved(test_user, single_row_valid_df):
    csv_upload_sync(test_user, single_row_valid_df)
    visit = Visit.objects.first()

    assert (
        visit.height_centile
        == MOCK_VISIT_EXTERNAL_VALIDATION_RESULT.height_result.centile
    )
    assert visit.height_sds == MOCK_VISIT_EXTERNAL_VALIDATION_RESULT.height_result.sds

    assert (
        visit.weight_centile
        == MOCK_VISIT_EXTERNAL_VALIDATION_RESULT.weight_result.centile
    )
    assert visit.weight_sds == MOCK_VISIT_EXTERNAL_VALIDATION_RESULT.weight_result.sds

    assert visit.bmi == MOCK_VISIT_EXTERNAL_VALIDATION_RESULT.bmi

    assert visit.bmi_centile == MOCK_VISIT_EXTERNAL_VALIDATION_RESULT.bmi_result.centile
    assert visit.bmi_sds == MOCK_VISIT_EXTERNAL_VALIDATION_RESULT.bmi_result.sds


"""
HbA1c tests
"""


@pytest.mark.django_db
def test_hba1c_value_ifcc_less_than_20(test_user, single_row_valid_df):
    single_row_valid_df.loc[0, "Hba1c Value"] = 18
    single_row_valid_df.loc[0, "HbA1c result format"] = 1  # IFCC (mmol/mol)
    single_row_valid_df.loc[0, "Observation Date: Hba1c Value"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hba1c" in errors[0]

    visit = Visit.objects.first()

    # This would be rejected in the questionnaire but saved if it was a csv upload
    assert visit.hba1c == 18
    assert "hba1c" in visit.errors


@pytest.mark.django_db
def test_hba1c_value_ifcc_more_than_195(test_user, single_row_valid_df):
    single_row_valid_df.loc[0, "Hba1c Value"] = 196
    single_row_valid_df.loc[0, "HbA1c result format"] = 1  # IFCC (mmol/mol)
    single_row_valid_df.loc[0, "Observation Date: Hba1c Value"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hba1c" in errors[0]

    visit = Visit.objects.first()

    # This would be rejected in the questionnaire but saved if it was a csv upload
    assert visit.hba1c == 196
    assert "hba1c" in visit.errors


@pytest.mark.django_db
def test_hba1c_value_dcct_more_than_20(test_user, single_row_valid_df):
    single_row_valid_df.loc[0, "Hba1c Value"] = 21
    single_row_valid_df.loc[0, "HbA1c result format"] = 2  # DCCT (%)
    single_row_valid_df.loc[0, "Observation Date: Hba1c Value"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hba1c" in errors[0]

    visit = Visit.objects.first()

    # This would be rejected in the questionnaire but saved if it was a csv upload
    assert visit.hba1c == 21
    assert "hba1c" in visit.errors


@pytest.mark.django_db
def test_hba1c_value_dcct_less_than_3(test_user, single_row_valid_df):
    single_row_valid_df.loc[0, "Hba1c Value"] = 2
    single_row_valid_df.loc[0, "HbA1c result format"] = 2  # DCCT (%)
    single_row_valid_df.loc[0, "Observation Date: Hba1c Value"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hba1c" in errors[0]

    visit = Visit.objects.first()

    # This would be rejected in the questionnaire but saved if it was a csv upload
    assert visit.hba1c == 2
    assert "hba1c" in visit.errors


@pytest.mark.django_db
def test_hba1c_missing(test_user, single_row_valid_df):
    single_row_valid_df.loc[0, "Hba1c Value"] = None
    single_row_valid_df.loc[0, "HbA1c result format"] = 2  # DCCT (%)
    single_row_valid_df.loc[0, "Observation Date: Hba1c Value"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hba1c" in errors[0]

    visit = Visit.objects.first()

    # This would be rejected in the questionnaire but saved if it was a csv upload
    assert visit.hba1c == None
    assert "hba1c" in visit.errors


"""
Diabetes treatment tests
"""


@pytest.mark.django_db
def test_treatment_closed_loop_passes_validation(test_user, single_row_valid_df):
    """
    Test that both pump and closed loop system are accepted
    """
    single_row_valid_df.loc[0, "Diabetes Treatment at time of Hba1c measurement"] = 3
    single_row_valid_df.loc[
        0,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 1

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert len(errors) == 0

    visit = Visit.objects.first()
    assert visit.treatment == 3
    assert visit.closed_loop_system == 1


@pytest.mark.django_db
def test_treatment_missing_closed_loop_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that both closed loop system selected but treatment is None fail validation
    """
    single_row_valid_df.loc[0, "Diabetes Treatment at time of Hba1c measurement"] = None
    single_row_valid_df.loc[
        0,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 1

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "treatment" in errors[0]

    visit = Visit.objects.first()
    assert visit.treatment is None
    assert visit.closed_loop_system == 1


@pytest.mark.django_db
def test_treatment_mdi_but_closed_loop_selected_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that MDI selected but closed loop system is also selected
    """
    single_row_valid_df.loc[0, "Diabetes Treatment at time of Hba1c measurement"] = (
        2  # MDI
    )
    single_row_valid_df.loc[
        0,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 2  # Closed loop system (licensed)

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert "closed_loop_system" in errors[0]

    visit = Visit.objects.first()
    assert visit.treatment == 2
    assert visit.closed_loop_system == 2
    assert "closed_loop_system" in visit.errors


"""
Blood pressure tests
"""


@pytest.mark.django_db
def test_blood_pressure_values_passes_validation(test_user, single_row_valid_df):
    """
    Test that both systolic and diastolic blood pressure values are accepted
    """
    single_row_valid_df.loc[0, "Systolic Blood Pressure"] = 120
    single_row_valid_df.loc[0, "Diastolic Blood pressure"] = (
        80  # Note that pressure has a lower case 'p'
    )
    single_row_valid_df.loc[0, "Observation Date (Blood Pressure)"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert len(errors) == 0

    visit = Visit.objects.first()
    assert visit.systolic_blood_pressure == 120
    assert visit.diastolic_blood_pressure == 80


@pytest.mark.django_db
def test_blood_pressure_missing_values_fails_validation(test_user, single_row_valid_df):
    """
    Test that one missing systolic blood pressure value fails validation
    """
    single_row_valid_df.loc[0, "Systolic Blood Pressure"] = None
    single_row_valid_df.loc[0, "Diastolic Blood pressure"] = (
        80  # Note that pressure has a lower case 'p'
    )
    single_row_valid_df.loc[0, "Observation Date (Blood Pressure)"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert (
        "systolic_blood_pressure" in errors[0]
    ), "Systolic Blood Pressure is None but passes validation."

    visit = Visit.objects.first()
    assert visit.systolic_blood_pressure == None
    assert visit.diastolic_blood_pressure == 80


@pytest.mark.django_db
def test_blood_pressure_missing_date_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that one missing blood pressure observation date fails validation
    """

    single_row_valid_df.loc[0, "Systolic Blood Pressure"] = 120
    single_row_valid_df.loc[0, "Diastolic Blood pressure"] = (
        80  # Note that pressure has a lower case 'p'
    )
    single_row_valid_df.loc[0, "Observation Date (Blood Pressure)"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert (
        "blood_pressure_observation_date" in errors[0]
    ), "Blood Pressure observation date is None but passes validation."

    visit = Visit.objects.first()
    assert (
        visit.systolic_blood_pressure == 120
    ), f"Systolic blood pressure should be 120 but was {visit.systolic_blood_pressure}"
    assert (
        visit.diastolic_blood_pressure == 80
    ), f"Diastolic blood pressure should be 80 but was {visit.diastolic_blood_pressure}"
    assert (
        visit.blood_pressure_observation_date is None
    ), f"Blood pressure observation date should be empty but is {visit.blood_pressure_observation_date}"


@pytest.mark.django_db
def test_systolic_blood_pressure_over_240_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that systolic blood pressure value > 240 fails validation
    """

    single_row_valid_df.loc[0, "Systolic Blood Pressure"] = 250
    single_row_valid_df.loc[0, "Diastolic Blood pressure"] = (
        80  # Note that pressure has a lower case 'p'
    )
    single_row_valid_df.loc[0, "Observation Date (Blood Pressure)"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert (
        "systolic_blood_pressure" in errors[0]
    ), "Systolic Blood Pressure is >240 (so really dangerously high!) but passes validation."

    visit = Visit.objects.first()
    assert (
        visit.systolic_blood_pressure == 250
    ), f"Systolic blood pressure should be 250 (and really the child should be in hospital) but was {visit.systolic_blood_pressure}"
    assert (
        visit.diastolic_blood_pressure == 80
    ), f"Diastolic blood pressure should be 80 but was {visit.diastolic_blood_pressure}"
    assert visit.blood_pressure_observation_date == datetime.date(
        2022, 1, 1
    ), f"Blood pressure observation date should be 1/1/2022 but is {visit.blood_pressure_observation_date}"


@pytest.mark.django_db
def test_systolic_blood_pressure_below_80_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that systolic blood pressure value < 80 fails validation
    """

    single_row_valid_df.loc[0, "Systolic Blood Pressure"] = 60
    single_row_valid_df.loc[0, "Diastolic Blood pressure"] = (
        40  # Note that pressure has a lower case 'p'
    )
    single_row_valid_df.loc[0, "Observation Date (Blood Pressure)"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert (
        "systolic_blood_pressure" in errors[0]
    ), "Systolic Blood Pressure is < 80 (so really dangerously low!) but passes validation."

    visit = Visit.objects.first()
    assert (
        visit.systolic_blood_pressure == 60
    ), f"Systolic blood pressure should be 60 (and really the child should be in hospital) but was {visit.systolic_blood_pressure}"
    assert (
        visit.diastolic_blood_pressure == 40
    ), f"Diastolic blood pressure should be 40 but was {visit.diastolic_blood_pressure}"
    assert visit.blood_pressure_observation_date == datetime.date(
        2022, 1, 1
    ), f"Blood pressure observation date should be 1/1/2022 but is {visit.blood_pressure_observation_date}"


@pytest.mark.django_db
def test_diastolic_blood_pressure_over_120_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that diastolic blood pressure value > 120 fails validation
    """

    single_row_valid_df.loc[0, "Systolic Blood Pressure"] = 120
    single_row_valid_df.loc[0, "Diastolic Blood pressure"] = (
        125  # Note that pressure has a lower case 'p'
    )
    single_row_valid_df.loc[0, "Observation Date (Blood Pressure)"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert (
        "diastolic_blood_pressure" in errors[0]
    ), "Diastolic Blood Pressure is >120 (so really dangerously high!) but passes validation."

    visit = Visit.objects.first()
    assert (
        visit.systolic_blood_pressure == 120
    ), f"Systolic blood pressure should be 120 but was {visit.systolic_blood_pressure}"
    assert (
        visit.diastolic_blood_pressure == 125
    ), f"Diastolic blood pressure should be 125 (and really the child should be in hospital) but was {visit.diastolic_blood_pressure}"
    assert visit.blood_pressure_observation_date == datetime.date(
        2022, 1, 1
    ), f"Blood pressure observation date should be 1/1/2022 but is {visit.blood_pressure_observation_date}"


@pytest.mark.django_db
def test_diastolic_blood_pressure_below_20_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that diastolic blood pressure value < 20 fails validation
    """

    single_row_valid_df.loc[0, "Systolic Blood Pressure"] = 120
    single_row_valid_df.loc[0, "Diastolic Blood pressure"] = (
        15  # Note that pressure has a lower case 'p'
    )
    single_row_valid_df.loc[0, "Observation Date (Blood Pressure)"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)
    assert (
        "diastolic_blood_pressure" in errors[0]
    ), "Diastolic Blood Pressure is < 20 (so really dangerously low!) but passes validation."

    visit = Visit.objects.first()
    assert (
        visit.systolic_blood_pressure == 120
    ), f"Systolic blood pressure should be 120 but was {visit.systolic_blood_pressure}"
    assert (
        visit.diastolic_blood_pressure == 15
    ), f"Diastolic blood pressure should be 15 (and really the child should be in hospital) but was {visit.diastolic_blood_pressure}"
    assert visit.blood_pressure_observation_date == datetime.date(
        2022, 1, 1
    ), f"Blood pressure observation date should be 1/1/2022 but is {visit.blood_pressure_observation_date}"


"""
Retinal screening tests
"""


@pytest.mark.django_db
def test_decs_value_form_passes_validation(test_user, single_row_valid_df):
    """
    Test that DECS value is accepted
    """
    single_row_valid_df.loc[0, "Retinal Screening date"] = "01/01/2022"
    single_row_valid_df.loc[0, "Retinal Screening Result"] = 1  # Normal

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        len(errors) == 0
    ), f"Retinal screening date and result should pass validation, but failed with errors: {errors}"

    visit = Visit.objects.first()
    assert visit.retinal_screening_observation_date == datetime.date(
        2022, 1, 1
    ), f"Saved Retinal screening date should be 1/1/2022, but was {visit.retinal_screening_observation_date}"
    assert (
        visit.retinal_screening_result == 1
    ), f"Saved Retinal screening result should be 1 (Normal), but was {visit.retinal_screening_result}"


@pytest.mark.django_db
def test_decs_value_unrecognized_form_fails_validation(test_user, single_row_valid_df):
    """
    Test that an impossible DECS value is invalid
    """
    single_row_valid_df.loc[0, "Retinal Screening date"] = "01/01/2022"
    single_row_valid_df.loc[0, "Retinal Screening Result"] = 94  # Impossible value

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "retinal_screening_result" in errors[0]
    ), f"Retinal screening result should fail validation, but passed."

    visit = Visit.objects.first()
    assert visit.retinal_screening_observation_date == datetime.date(
        2022, 1, 1
    ), f"Saved Retinal screening date should be 1/1/2022, but was {visit.retinal_screening_observation_date}"
    assert (
        visit.retinal_screening_result == 94
    ), f"Saved Retinal screening result should be 94 (impossible value), but was {visit.retinal_screening_result}"


@pytest.mark.django_db
def test_decs_value_none_form_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing DECS value is invalid
    """
    single_row_valid_df.loc[0, "Retinal Screening date"] = "01/01/2022"
    single_row_valid_df.loc[0, "Retinal Screening Result"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "retinal_screening_result" in errors[0]
    ), f"Retinal screening result should fail validation due to missing result, but passed."

    visit = Visit.objects.first()
    assert visit.retinal_screening_observation_date == datetime.date(
        2022, 1, 1
    ), f"Saved Retinal screening date should be 1/1/2022, but was {visit.retinal_screening_observation_date}"
    assert (
        visit.retinal_screening_result == None
    ), f"Saved Retinal screening result should be None, but was {visit.retinal_screening_result}"


@pytest.mark.django_db
def test_decs_date_none_form_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing DECS date is invalid
    """
    single_row_valid_df.loc[0, "Retinal Screening date"] = None
    single_row_valid_df.loc[0, "Retinal Screening Result"] = 1  # Normal

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "retinal_screening_observation_date" in errors[0]
    ), f"Retinal screening date should fail validation due to missing date, but passed."

    visit = Visit.objects.first()
    assert (
        visit.retinal_screening_observation_date == None
    ), f"Saved Retinal screening date should be None, but was {visit.retinal_screening_observation_date}"
    assert (
        visit.retinal_screening_result == 1
    ), f"Saved Retinal screening result should be 1 (Normal), but was {visit.retinal_screening_result}"


"""
Urine albumin tests
"""


@pytest.mark.django_db
def test_urine_albumin_value_form_passes_validation(test_user, single_row_valid_df):
    """
    Test that urine albumin value is accepted
    """
    single_row_valid_df.loc[0, "Urinary Albumin Level (ACR)"] = 30
    single_row_valid_df.loc[0, "Albuminuria Stage"] = 1  # Normal
    single_row_valid_df.loc[0, "Observation Date: Urinary Albumin Level"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert (
        visit.albumin_creatinine_ratio == 30
    ), f"Saved urine albumin should be 30, but was {visit.albumin_creatinine_ratio}"
    assert (
        visit.albuminuria_stage == 1
    ), f"Saved urine albumin stage should be 1 (Normal), but was {visit.albuminuria_stage}"
    assert visit.albumin_creatinine_ratio_date == datetime.date(
        2022, 1, 1
    ), f"Saved urine albumin observation date should be 1/1/2022, but was {visit.albumin_creatinine_ratio_date}"


@pytest.mark.django_db
def test_urine_albumin_impossible_value_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that urine albumin stage is rejected if impossible
    """
    single_row_valid_df.loc[0, "Urinary Albumin Level (ACR)"] = 30
    single_row_valid_df.loc[0, "Albuminuria Stage"] = 94  # Impossible value
    single_row_valid_df.loc[0, "Observation Date: Urinary Albumin Level"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "albuminuria_stage" in errors[0]
    ), f"Urine albumin stage should fail validation as impossible, but passed."

    visit = Visit.objects.first()

    assert (
        visit.albumin_creatinine_ratio == 30
    ), f"Saved urine albumin should be 30, but was {visit.albumin_creatinine_ratio}"
    assert (
        visit.albuminuria_stage == 94
    ), f"Saved urine albumin stage should be 94 (Impossible), but was {visit.albuminuria_stage}"
    assert visit.albumin_creatinine_ratio_date == datetime.date(
        2022, 1, 1
    ), f"Saved urine albumin observation date should be 1/1/2022, but was {visit.albumin_creatinine_ratio_date}"


@pytest.mark.django_db
def test_urine_albumin_value_below_range_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that urine albumin value is rejected if below range
    """
    single_row_valid_df.loc[0, "Urinary Albumin Level (ACR)"] = 0.1
    single_row_valid_df.loc[0, "Albuminuria Stage"] = 1  # Normal
    single_row_valid_df.loc[0, "Observation Date: Urinary Albumin Level"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "albumin_creatinine_ratio" in errors[0]
    ), f"Urine albumin creatinine ratio should fail validation as < 3, but passed."

    visit = Visit.objects.first()

    assert visit.albumin_creatinine_ratio == Decimal(
        "0.1"
    ), f"Saved urine albumin should be 0.1, but was {visit.albumin_creatinine_ratio}"
    assert (
        visit.albuminuria_stage == 1
    ), f"Saved urine albumin stage should be 1 (Normal), but was {visit.albuminuria_stage}"
    assert visit.albumin_creatinine_ratio_date == datetime.date(
        2022, 1, 1
    ), f"Saved urine albumin observation date should be 1/1/2022, but was {visit.albumin_creatinine_ratio_date}"


@pytest.mark.django_db
def test_urine_albumin_value_above_range_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that urine albumin value is rejected if above range
    """
    single_row_valid_df.loc[0, "Urinary Albumin Level (ACR)"] = 100
    single_row_valid_df.loc[0, "Albuminuria Stage"] = 1  # Normal
    single_row_valid_df.loc[0, "Observation Date: Urinary Albumin Level"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "albumin_creatinine_ratio" in errors[0]
    ), f"Urine albumin creatinine ratio should fail validation as > 50, but passed."

    visit = Visit.objects.first()

    assert (
        visit.albumin_creatinine_ratio == 100
    ), f"Saved urine albumin should be 100, but was {visit.albumin_creatinine_ratio}"
    assert (
        visit.albuminuria_stage == 1
    ), f"Saved urine albumin stage should be 1 (Normal), but was {visit.albuminuria_stage}"
    assert visit.albumin_creatinine_ratio_date == datetime.date(
        2022, 1, 1
    ), f"Saved urine albumin observation date should be 1/1/2022, but was {visit.albumin_creatinine_ratio_date}"


@pytest.mark.django_db
def test_urine_albumin_value_missing_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that urine albumin value missing  is rejected
    """
    single_row_valid_df.loc[0, "Urinary Albumin Level (ACR)"] = None
    single_row_valid_df.loc[0, "Albuminuria Stage"] = 1  # Normal
    single_row_valid_df.loc[0, "Observation Date: Urinary Albumin Level"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "albumin_creatinine_ratio" in errors[0]
    ), f"Urine albumin creatinine level should fail validation as None, but passed."

    visit = Visit.objects.first()

    assert (
        visit.albumin_creatinine_ratio is None
    ), f"Saved urine albumin should be None, but was {visit.albumin_creatinine_ratio}"
    assert (
        visit.albuminuria_stage == 1
    ), f"Saved urine albumin stage should be 1 (Normal), but was {visit.albuminuria_stage}"
    assert visit.albumin_creatinine_ratio_date == datetime.date(
        2022, 1, 1
    ), f"Saved urine albumin observation date should be 1/1/2022, but was {visit.albumin_creatinine_ratio_date}"


@pytest.mark.django_db
def test_urine_albumin_stage_missing_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that urine albumin value missing  is rejected
    """
    single_row_valid_df.loc[0, "Urinary Albumin Level (ACR)"] = 10
    single_row_valid_df.loc[0, "Albuminuria Stage"] = None
    single_row_valid_df.loc[0, "Observation Date: Urinary Albumin Level"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "albuminuria_stage" in errors[0]
    ), f"Urine albumin creatinine stage should fail validation as None, but passed."

    visit = Visit.objects.first()

    assert (
        visit.albumin_creatinine_ratio == 10
    ), f"Saved urine albumin should be 10, but was {visit.albumin_creatinine_ratio}"
    assert (
        visit.albuminuria_stage == None
    ), f"Saved urine albumin stage should be None, but was {visit.albuminuria_stage}"
    assert visit.albumin_creatinine_ratio_date == datetime.date(
        2022, 1, 1
    ), f"Saved urine albumin observation date should be 1/1/2022, but was {visit.albumin_creatinine_ratio_date}"


@pytest.mark.django_db
def test_urine_albumin_date_missing_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that urine albumin date missing is rejected
    """
    single_row_valid_df.loc[0, "Urinary Albumin Level (ACR)"] = 10
    single_row_valid_df.loc[0, "Albuminuria Stage"] = 1  # Normal
    single_row_valid_df.loc[0, "Observation Date: Urinary Albumin Level"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "albumin_creatinine_ratio_date" in errors[0]
    ), f"Urine albumin creatinine date should fail validation as None, but passed."

    visit = Visit.objects.first()

    assert (
        visit.albumin_creatinine_ratio == 10
    ), f"Saved urine albumin should be 10, but was {visit.albumin_creatinine_ratio}"
    assert (
        visit.albuminuria_stage == 1
    ), f"Saved urine albumin stage should be 1 (Normal), but was {visit.albuminuria_stage}"
    assert (
        visit.albumin_creatinine_ratio_date == None
    ), f"Saved urine albumin observation date should be None, but was {visit.albumin_creatinine_ratio_date}"


"""
Total cholesterol tests
"""


@pytest.mark.django_db
def test_total_cholesterol_value_form_passes_validation(test_user, single_row_valid_df):
    """
    Test that total cholesterol value is accepted
    """
    single_row_valid_df.loc[0, "Total Cholesterol Level (mmol/l)"] = 5
    single_row_valid_df.loc[0, "Observation Date: Total Cholesterol Level"] = (
        "01/01/2022"
    )

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert (
        visit.total_cholesterol == 5
    ), f"Saved total cholesterol should be 5, but was {visit.total_cholesterol}"
    assert visit.total_cholesterol_date == datetime.date(
        2022, 1, 1
    ), f"Saved total cholesterol observation date should be 1/1/2022, but was {visit.total_cholesterol_date}"


@pytest.mark.django_db
def test_total_cholesterol_value_above_reference_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that total cholesterol value is rejected if impossible
    """
    single_row_valid_df.loc[0, "Total Cholesterol Level (mmol/l)"] = 20
    single_row_valid_df.loc[0, "Observation Date: Total Cholesterol Level"] = (
        "01/01/2022"
    )

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "total_cholesterol" in errors[0]
    ), f"Total cholesterol should fail validation as above reference range, but passed."

    visit = Visit.objects.first()

    assert (
        visit.total_cholesterol == 20
    ), f"Saved total cholesterol should be 1000, but was {visit.total_cholesterol}"
    assert visit.total_cholesterol_date == datetime.date(
        2022, 1, 1
    ), f"Saved total cholesterol observation date should be 1/1/2022, but was {visit.total_cholesterol_date}"


@pytest.mark.django_db
def test_total_cholesterol_value_below_reference_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that total cholesterol value is rejected if impossible
    """
    single_row_valid_df.loc[0, "Total Cholesterol Level (mmol/l)"] = Decimal("0.1")
    single_row_valid_df.loc[0, "Observation Date: Total Cholesterol Level"] = (
        "01/01/2022"
    )

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "total_cholesterol" in errors[0]
    ), f"Total cholesterol should fail validation as impossible, but passed."

    visit = Visit.objects.first()

    assert visit.total_cholesterol == Decimal(
        "0.1"
    ), f"Saved total cholesterol should be 0, but was {visit.total_cholesterol}"
    assert visit.total_cholesterol_date == datetime.date(
        2022, 1, 1
    ), f"Saved total cholesterol observation date should be 1/1/2022, but was {visit.total_cholesterol_date}"


@pytest.mark.django_db
def test_total_cholesterol_value_missing_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that total cholesterol value missing  is rejected
    """
    single_row_valid_df.loc[0, "Total Cholesterol Level (mmol/l)"] = None
    single_row_valid_df.loc[0, "Observation Date: Total Cholesterol Level"] = (
        "01/01/2022"
    )

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "total_cholesterol" in errors[0]
    ), f"Total cholesterol should fail validation as None, but passed."

    visit = Visit.objects.first()

    assert (
        visit.total_cholesterol is None
    ), f"Saved total cholesterol should be None, but was {visit.total_cholesterol}"
    assert visit.total_cholesterol_date == datetime.date(
        2022, 1, 1
    ), f"Saved total cholesterol observation date should be 1/1/2022, but was {visit.total_cholesterol_date}"


@pytest.mark.django_db
def test_total_cholesterol_date_missing_form_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that total cholesterol date missing is rejected
    """
    single_row_valid_df.loc[0, "Total Cholesterol Level (mmol/l)"] = 5
    single_row_valid_df.loc[0, "Observation Date: Total Cholesterol Level"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "total_cholesterol_date" in errors[0]
    ), f"Total cholesterol date should fail validation as None, but passed."

    visit = Visit.objects.first()

    assert (
        visit.total_cholesterol == 5
    ), f"Saved total cholesterol should be 5, but was {visit.total_cholesterol}"
    assert (
        visit.total_cholesterol_date == None
    ), f"Saved total cholesterol observation date should be None, but was {visit.total_cholesterol_date}"


"""
Thyroid treatment tests
"""


@pytest.mark.django_db
def test_thyroid_treatment_passes_validation(test_user, single_row_valid_df):
    """
    Test that thyroid treatment is accepted
    """
    single_row_valid_df.loc[
        0,
        "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
    ] = 1  # Normal
    single_row_valid_df.loc[0, "Observation Date: Thyroid Function"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.thyroid_treatment_status == 1
    assert visit.thyroid_function_date == datetime.date(2022, 1, 1)


@pytest.mark.django_db
def test_thyroid_treatment_impossible_value_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that an impossible thyroid treatment value is rejected
    """
    single_row_valid_df.loc[
        0,
        "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
    ] = 94  # Impossible value
    single_row_valid_df.loc[0, "Observation Date: Thyroid Function"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "thyroid_treatment_status" in errors[0]

    visit = Visit.objects.first()

    assert visit.thyroid_treatment_status == 94
    assert visit.thyroid_function_date == datetime.date(2022, 1, 1)


@pytest.mark.django_db
def test_thyroid_treatment_missing_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing thyroid treatment value is rejected
    """
    single_row_valid_df.loc[
        0,
        "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
    ] = None
    single_row_valid_df.loc[0, "Observation Date: Thyroid Function"] = "01/01/2022"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "thyroid_treatment_status" in errors[0]

    visit = Visit.objects.first()

    assert visit.thyroid_treatment_status is None
    assert visit.thyroid_function_date == datetime.date(2022, 1, 1)


@pytest.mark.django_db
def test_thyroid_treatment_date_missing_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that a missing thyroid treatment date is rejected
    """
    single_row_valid_df.loc[
        0,
        "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
    ] = 1
    single_row_valid_df.loc[0, "Observation Date: Thyroid Function"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "thyroid_function_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.thyroid_treatment_status == 1
    assert visit.thyroid_function_date is None


"""
Coeliac screening tests
"""


@pytest.mark.django_db
def test_coeliac_screening_passes_validation(test_user, single_row_valid_df):
    """
    Test that coeliac screening is accepted
    """
    single_row_valid_df.loc[0, "Observation Date: Coeliac Disease Screening"] = (
        "01/01/2022"
    )
    single_row_valid_df.loc[
        0, "Has the patient been recommended a Gluten-free diet?"
    ] = 1  # Yes

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.coeliac_screen_date == datetime.date(2022, 1, 1)
    assert visit.gluten_free_diet == 1


@pytest.mark.django_db
def test_coeliac_screening_impossible_value_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that an impossible coeliac screening value is rejected
    """
    single_row_valid_df.loc[0, "Observation Date: Coeliac Disease Screening"] = (
        "01/01/2022"
    )
    single_row_valid_df.loc[
        0, "Has the patient been recommended a Gluten-free diet?"
    ] = 94  # Impossible value

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "gluten_free_diet" in errors[0]

    visit = Visit.objects.first()

    assert visit.coeliac_screen_date == datetime.date(2022, 1, 1)
    assert visit.gluten_free_diet == 94


@pytest.mark.django_db
def test_coeliac_screening_missing_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing coeliac screening value is rejected
    """
    single_row_valid_df.loc[0, "Observation Date: Coeliac Disease Screening"] = (
        "01/01/2022"
    )
    single_row_valid_df.loc[
        0, "Has the patient been recommended a Gluten-free diet?"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "gluten_free_diet" in errors[0]

    visit = Visit.objects.first()

    assert visit.coeliac_screen_date == datetime.date(2022, 1, 1)
    assert visit.gluten_free_diet is None


@pytest.mark.django_db
def test_coeliac_screening_date_missing_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that a missing coeliac screening date is rejected
    """
    single_row_valid_df.loc[0, "Observation Date: Coeliac Disease Screening"] = None
    single_row_valid_df.loc[
        0, "Has the patient been recommended a Gluten-free diet?"
    ] = 1

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "coeliac_screen_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.coeliac_screen_date is None
    assert visit.gluten_free_diet == 1


"""
Psychological support tests
"""


@pytest.mark.django_db
def test_psychological_support_passes_validation(test_user, single_row_valid_df):
    """
    Test that psychological support is accepted
    """
    single_row_valid_df.loc[
        0, "Observation Date - Psychological Screening Assessment"
    ] = "01/01/2022"
    single_row_valid_df.loc[
        0,
        "Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?",
    ] = 1

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.psychological_screening_assessment_date == datetime.date(2022, 1, 1)
    assert visit.psychological_additional_support_status == 1


@pytest.mark.django_db
def test_psychological_support_impossible_value_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that an impossible psychological support value is rejected
    """
    single_row_valid_df.loc[
        0, "Observation Date - Psychological Screening Assessment"
    ] = "01/01/2022"
    single_row_valid_df.loc[
        0,
        "Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?",
    ] = 94  # Impossible value

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "psychological_additional_support_status" in errors[0]

    visit = Visit.objects.first()

    assert visit.psychological_screening_assessment_date == datetime.date(2022, 1, 1)
    assert visit.psychological_additional_support_status == 94


@pytest.mark.django_db
def test_psychological_support_missing_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing psychological support value is rejected
    """
    single_row_valid_df.loc[
        0, "Observation Date - Psychological Screening Assessment"
    ] = "01/01/2022"
    single_row_valid_df.loc[
        0,
        "Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?",
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "psychological_additional_support_status" in errors[0]

    visit = Visit.objects.first()

    assert visit.psychological_screening_assessment_date == datetime.date(2022, 1, 1)
    assert visit.psychological_additional_support_status is None


@pytest.mark.django_db
def test_psychological_support_date_missing_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that a missing psychological support date is rejected
    """
    single_row_valid_df.loc[
        0, "Observation Date - Psychological Screening Assessment"
    ] = None
    single_row_valid_df.loc[
        0,
        "Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?",
    ] = 1

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "psychological_screening_assessment_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.psychological_screening_assessment_date is None
    assert visit.psychological_additional_support_status == 1


"""
Smoking status tests
"""


@pytest.mark.django_db
def test_smoking_status_passes_validation(test_user, single_row_valid_df):
    """
    Test that smoking status is accepted
    """
    single_row_valid_df.loc[
        0,
        "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    ] = "01/01/2022"
    single_row_valid_df.loc[0, "Does the patient smoke?"] = 2  # Current smoker

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.smoking_cessation_referral_date == datetime.date(2022, 1, 1)
    assert visit.smoking_status == 2


@pytest.mark.django_db
def test_smoking_status_non_smoker_passes_validation(test_user, single_row_valid_df):
    """
    Test that smoking status is accepted
    """
    single_row_valid_df.loc[
        0,
        "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    ] = None
    single_row_valid_df.loc[0, "Does the patient smoke?"] = 1  # Non-smoker

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.smoking_cessation_referral_date is None
    assert visit.smoking_status == 1


@pytest.mark.django_db
def test_smoking_status_impossible_value_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that an impossible smoking status value is rejected
    """
    single_row_valid_df.loc[
        0,
        "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    ] = "01/01/2022"
    single_row_valid_df.loc[0, "Does the patient smoke?"] = 94  # Impossible value

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "smoking_status" in errors[0]

    visit = Visit.objects.first()

    assert visit.smoking_cessation_referral_date == datetime.date(2022, 1, 1)
    assert visit.smoking_status == 94


@pytest.mark.django_db
def test_smoking_status_non_smoker_referral_date_provided_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that a non-smoker with a referral date is rejected
    """
    single_row_valid_df.loc[
        0,
        "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    ] = "01/01/2022"
    single_row_valid_df.loc[0, "Does the patient smoke?"] = 1  # Non-smoker

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "smoking_cessation_referral_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.smoking_cessation_referral_date == datetime.date(2022, 1, 1)
    assert visit.smoking_status == 1


@pytest.mark.django_db
def test_smoking_status_missing_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing smoking status value is rejected
    """
    single_row_valid_df.loc[
        0,
        "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    ] = "01/01/2022"
    single_row_valid_df.loc[0, "Does the patient smoke?"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "smoking_cessation_referral_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.smoking_cessation_referral_date == datetime.date(2022, 1, 1)
    assert visit.smoking_status is None


@pytest.mark.django_db
def test_smoking_status_date_missing_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing smoking status date is rejected
    """
    single_row_valid_df.loc[
        0,
        "Date of offer of referral to smoking cessation service (if patient is a current smoker)",
    ] = None
    single_row_valid_df.loc[0, "Does the patient smoke?"] = 2  # Current smoker

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "smoking_cessation_referral_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.smoking_status is 2
    assert visit.smoking_cessation_referral_date is None


"""
Dietitian referral tests
"""


@pytest.mark.django_db
def test_dietician_referral_status_additional_offered_form_passes_validation(
    test_user, single_row_valid_df
):
    """
    Test that dietician referral status and date are accepted
    """
    single_row_valid_df.loc[
        0,
        "Was the patient offered an additional appointment with a paediatric dietitian?",
    ] = 1
    single_row_valid_df.loc[0, "Date of additional appointment with dietitian"] = (
        "01/01/2022"
    )

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.dietician_additional_appointment_offered == 1
    assert visit.dietician_additional_appointment_date == datetime.date(2022, 1, 1)


@pytest.mark.django_db
def test_dietician_no_additional_offered_form_passes_validation(
    test_user, single_row_valid_df
):
    """
    Test that dietician referral status and date are accepted
    """
    single_row_valid_df.loc[
        0,
        "Was the patient offered an additional appointment with a paediatric dietitian?",
    ] = 2
    single_row_valid_df.loc[0, "Date of additional appointment with dietitian"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.dietician_additional_appointment_offered == 2
    assert visit.dietician_additional_appointment_date is None


@pytest.mark.django_db
def test_dietician_no_additional_offered_date_provided_fail_validation(
    test_user, single_row_valid_df
):
    """
    Test that dietician extra appointment not offered but date provided should fail
    """
    single_row_valid_df.loc[
        0,
        "Was the patient offered an additional appointment with a paediatric dietitian?",
    ] = 2
    single_row_valid_df.loc[0, "Date of additional appointment with dietitian"] = (
        "01/01/2022"
    )

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "dietician_additional_appointment_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.dietician_additional_appointment_offered == 2
    assert visit.dietician_additional_appointment_date == datetime.date(2022, 1, 1)


@pytest.mark.django_db
def test_dietician_additional_offered_date_missing_fail_validation(
    test_user, single_row_valid_df
):
    """
    Test that dietician extra appointment offered but date missing should fail
    """
    single_row_valid_df.loc[
        0,
        "Was the patient offered an additional appointment with a paediatric dietitian?",
    ] = 1
    single_row_valid_df.loc[0, "Date of additional appointment with dietitian"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "dietician_additional_appointment_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.dietician_additional_appointment_offered == 1
    assert visit.dietician_additional_appointment_date is None


@pytest.mark.django_db
def test_dietician_additional_offered_none_but_date_offered_fail_validation(
    test_user, single_row_valid_df
):
    """
    Test that dietician additional appointment none but date offered should fail
    """
    single_row_valid_df.loc[
        0,
        "Was the patient offered an additional appointment with a paediatric dietitian?",
    ] = None
    single_row_valid_df.loc[0, "Date of additional appointment with dietitian"] = (
        "01/01/2022"
    )

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "dietician_additional_appointment_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.dietician_additional_appointment_offered is None
    assert visit.dietician_additional_appointment_date == datetime.date(2022, 1, 1)


"""
Sick day rules tests
"""


@pytest.mark.django_db
def test_sick_day_rules_provided_passes_validation(test_user, single_row_valid_df):
    """
    Test that sick day rules are accepted
    """
    single_row_valid_df.loc[
        0,
        "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
    ] = "01/01/2022"
    single_row_valid_df.loc[
        0,
        "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
    ] = 1

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.sick_day_rules_training_date == datetime.date(2022, 1, 1)
    assert visit.ketone_meter_training == 1


@pytest.mark.django_db
def test_sick_day_rules_not_provided_passes_validation(test_user, single_row_valid_df):
    """
    Test that sick day rules are accepted where not provided (date not required)
    """
    single_row_valid_df.loc[
        0,
        "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
    ] = None
    single_row_valid_df.loc[
        0,
        "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
    ] = 2

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.sick_day_rules_training_date == None
    assert visit.ketone_meter_training == 2


@pytest.mark.django_db
def test_sick_day_rules_not_provided_but_date_provided_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that sick day rules not provided but date provided fails validation
    """
    single_row_valid_df.loc[
        0,
        "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
    ] = "01/01/2022"
    single_row_valid_df.loc[
        0,
        "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
    ] = 2

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "ketone_meter_training" in errors[0]
    ), f"Expected error in sick_day_rules_training_date, but got None"

    visit = Visit.objects.first()

    assert visit.sick_day_rules_training_date == datetime.date(2022, 1, 1)
    assert visit.ketone_meter_training == 2


@pytest.mark.django_db
def test_sick_day_rules_none_but_date_provided_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that sick day rules not answered but date provided fails validation
    """
    single_row_valid_df.loc[
        0,
        "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
    ] = "01/01/2022"
    single_row_valid_df.loc[
        0,
        "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "ketone_meter_training" in errors[0]
    ), f"Expected error in sick_day_rules_training_date, but got None"

    visit = Visit.objects.first()

    assert visit.sick_day_rules_training_date == datetime.date(2022, 1, 1)
    assert visit.ketone_meter_training == None


@pytest.mark.django_db
def test_sick_day_rules_provided_but_no_date_provided_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that sick day rules are provided but no date is rejected
    """
    single_row_valid_df.loc[
        0,
        "Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
    ] = None
    single_row_valid_df.loc[
        0,
        "Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
    ] = 1

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert (
        "sick_day_rules_training_date" in errors[0]
    ), f"Expected error in sick_day_rules_training_date, but got None"

    visit = Visit.objects.first()

    assert visit.sick_day_rules_training_date == None
    assert visit.ketone_meter_training == 1


"""
Inpatient admission tests
"""


@pytest.mark.django_db
def test_inpatient_admission_stabilisation_passes_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for stabilisation is accepted
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/02/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 1  # Stabilisation
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 2
    ), f"Discharge date should be 2/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 1
    ), f"Admission reason should be 1 (stabilisation), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == None
    ), f"DKA additional therapies should be None, but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_stabilisation_missing_date_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for stabilisation is rejected if date missing
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = None
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/02/2024"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 1
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hospital_admission_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == None
    assert visit.hospital_discharge_date == datetime.date(year=2024, month=1, day=2)
    assert visit.hospital_admission_reason == 1
    assert visit.dka_additional_therapies == None
    assert visit.hospital_admission_other == None


@pytest.mark.django_db
def test_inpatient_admission_stabilisation_discharge_date_before_admission_date_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for stabilisation is rejected if discharge date before admission date
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 1
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hospital_admission_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(year=2022, month=1, day=8)
    assert visit.hospital_discharge_date == datetime.date(year=2022, month=1, day=1)
    assert visit.hospital_admission_reason == 1
    assert visit.dka_additional_therapies == None
    assert visit.hospital_admission_other == None


@pytest.mark.django_db
def test_inpatient_admission_stabilisation_discharge_date_before_diagnosis_date_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for stabilisation is rejected if discharge date before admission date
    """
    single_row_valid_df.loc[0, "Date of Diabetes Diagnosis"] = "1/10/2022"  # mm/dd/yyyy
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 1
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hospital_discharge_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.patient.diagnosis_date == datetime.date(
        2022, 1, 10
    ), f"Diagnosis date should be 1/1/2022, but was {visit.patient.diagnosis_date}"
    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 1
    ), f"Admission reason should be 1 (stabilisation), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == None
    ), f"DKA additional therapies should be None, but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_stabilisation_discharge_date_after_date_of_death_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for stabilisation is rejected if discharge date before admission date
    """
    single_row_valid_df.loc[0, "Death Date"] = "01/01/2022"
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = "01/01/2022"
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 1
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hospital_discharge_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.patient.death_date == datetime.date(
        2022, 1, 1
    ), f"Date of death should be 1/1/2022, but was {visit.patient.date_of_death}"
    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 1
    ), f"Admission reason should be 1 (stabilisation), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == None
    ), f"DKA additional therapies should be None, but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_stabilisation_dka_additional_therapies_provided_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for stabilisation is rejected if DKA additional therapies provided
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 1  # Stabilisation
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = 1  # Hypertonic saline
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "dka_additional_therapies" in errors[0]

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 1
    ), f"Admission reason should be 1 (stabilisation), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == 1
    ), f"DKA additional therapies should be 1 (hypertonic saline), but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_stabilisation_hospital_admission_other_provided_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for stabilisation is rejected if DKA additional therapies provided
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 1  # Stabilisation
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = 1  # Hypertonic saline
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "dka_additional_therapies" in errors[0]

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 1
    ), f"Admission reason should be 1 (stabilisation), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == 1
    ), f"DKA additional therapies should be 1 (hypertonic saline), but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_dka_passes_validation(test_user, single_row_valid_df):
    """
    Test that inpatient admission for DKA with additional therapies is accepted
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 2  # DKA
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = 1  # Hypertonic saline
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 2
    ), f"Admission reason should be 2 (DKA), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == 1
    ), f"DKA additional therapies should be 1 (hypertonic saline), but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_dka_additional_therapies_missing_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for DKA without additional therapies is rejected
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 2  # DKA
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "dka_additional_therapies" in errors[0]

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 2
    ), f"Admission reason should be 2 (DKA), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == None
    ), f"DKA additional therapies should be None, but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_dka_additional_therapies_hospital_admission_also_provided_fails_validation(
    test_user, single_row_valid_df
):
    """
    Tests that a hospital admission for DKA with additional therapies is rejected if hospital admission other is provided
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 2  # DKA
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = 1  # Hypertonic saline
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = "Other reason"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hospital_admission_other" in errors[0]

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 2
    ), f"Admission reason should be 2 (DKA), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == 1
    ), f"DKA additional therapies should be 1 (hypertonic saline), but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == "Other reason"
    ), f"Admission other should be 'Other reason', but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_other_passes_validation(test_user, single_row_valid_df):
    """
    Test that inpatient admission for other reason is accepted
    """
    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 6  # Other
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = "Other reason"

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 6
    ), f"Admission reason should be 6 (other), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == None
    ), f"DKA additional therapies should be None, but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == "Other reason"
    ), f"Admission other should be 'Other reason', but was {visit.hospital_admission_other}"


@pytest.mark.django_db
def test_inpatient_admission_other_missing_fails_validation(
    test_user, single_row_valid_df
):
    """
    Test that inpatient admission for other reason is rejected if reason missing
    """

    single_row_valid_df.loc[0, "Start date (Hospital Provider Spell)"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Discharge date (Hospital provider spell)"] = (
        "01/08/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Reason for admission"] = 6  # Other
    single_row_valid_df.loc[
        0,
        "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
    ] = None
    single_row_valid_df.loc[
        0, "Only complete if OTHER selected: Reason for admission (free text)"
    ] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "hospital_admission_other" in errors[0]

    visit = Visit.objects.first()

    assert visit.hospital_admission_date == datetime.date(
        2022, 1, 1
    ), f"Admission date should be 1/1/2022, but was {visit.hospital_admission_date}"
    assert visit.hospital_discharge_date == datetime.date(
        2022, 1, 8
    ), f"Discharge date should be 8/1/2022, but was {visit.hospital_discharge_date}"
    assert (
        visit.hospital_admission_reason == 6
    ), f"Admission reason should be 6 (other), but was {visit.hospital_admission_reason}"
    assert (
        visit.dka_additional_therapies == None
    ), f"DKA additional therapies should be None, but was {visit.dka_additional_therapies}"
    assert (
        visit.hospital_admission_other == None
    ), f"Admission other should be None, but was {visit.hospital_admission_other}"


"""
Visit date tests
"""


@pytest.mark.django_db
def test_visit_date_provided_passes_validation(test_user, single_row_valid_df):
    """
    Test that a visit date is accepted
    """
    single_row_valid_df.loc[0, "Visit/Appointment Date"] = "01/01/2025"  # mm/dd/yyyy

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert len(errors) == 0

    visit = Visit.objects.first()

    assert visit.visit_date == datetime.date(
        2025, 1, 1
    ), f"Visit/Appointment Date should be 1/1/2025, but was {visit.visit_date}"


@pytest.mark.django_db
def test_visit_date_missing_fails_validation(test_user, single_row_valid_df):
    """
    Test that a missing Visit/Appointment Date is rejected
    """
    single_row_valid_df.loc[0, "Visit/Appointment Date"] = None

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "visit_date" in errors[0], f"Expected error in visit_date, but got None"

    visit = Visit.objects.first()

    assert (
        visit.visit_date == None
    ), f"Visit/Appointment Date should be None, but was {visit.visit_date}"


@pytest.mark.django_db
def test_visit_date_not_before_date_of_birth(test_user, single_row_valid_df):
    """
    Test that a Visit/Appointment Date before the date of birth is rejected
    """
    single_row_valid_df.loc[0, "Date of Birth"] = "01/01/2022"
    single_row_valid_df.loc[0, "Visit/Appointment Date"] = "01/01/2021"  # mm/dd/yyyy

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "visit_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.visit_date == datetime.date(
        2021, 1, 1
    ), f"Visit date should be 1/1/2021, but was {visit.visit_date}"
    assert visit.patient.date_of_birth == datetime.date(
        2022, 1, 1
    ), f"Date of birth should be 1/1/2022, but was {visit.patient.date_of_birth}"


@pytest.mark.django_db
def test_visit_date_not_after_date_of_death(test_user, single_row_valid_df):
    """
    Test that a Visit/Appointment Date after the date of death is rejected
    """
    single_row_valid_df.loc[0, "Death Date"] = "01/01/2022"  # mm/dd/yyyy
    single_row_valid_df.loc[0, "Visit/Appointment Date"] = "01/01/2023"  # mm/dd/yyyy

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "visit_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.visit_date == datetime.date(
        2023, 1, 1
    ), f"Visit date should be 1/1/2023, but was {visit.visit_date}"
    assert visit.patient.death_date == datetime.date(
        2022, 1, 1
    ), f"Death date should be 1/1/2022, but was {visit.patient.death_date}"


@pytest.mark.django_db
def test_visit_date_not_before_diagnosis_date(test_user, single_row_valid_df):
    """
    Test that a Visit/Appointment Date before the date of diagnosis is rejected
    """
    single_row_valid_df.loc[0, "Date of Diabetes Diagnosis"] = (
        "01/01/2022"  # mm/dd/yyyy
    )
    single_row_valid_df.loc[0, "Visit/Appointment Date"] = "01/01/2021"  # mm/dd/yyyy

    errors = csv_upload_sync(test_user, single_row_valid_df)

    assert "visit_date" in errors[0]

    visit = Visit.objects.first()

    assert visit.visit_date == datetime.date(
        year=2021, month=1, day=1
    ), f"Visit date should be 1/1/2021, but was {visit.visit_date}"
    assert visit.patient.diagnosis_date == datetime.date(
        year=2022, month=1, day=1
    ), f"Diagnosis date should be 1/1/2022, but was {visit.patient.diagnosis_date}"
