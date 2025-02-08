import dataclasses
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
    df.loc[
        1,
        "If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
    ] = 3

    errors = csv_upload_sync(test_user, df)
    assert "treatment" in errors[0]

    assert Visit.objects.count() == 2

    [first_visit, second_visit] = Visit.objects.all().order_by("visit_date")

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
