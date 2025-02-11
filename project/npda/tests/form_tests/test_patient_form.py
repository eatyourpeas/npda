# Standard imports
import pytest
import logging
import dataclasses
from unittest.mock import Mock, patch
from unittest import skip

# 3rd Party imports
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

# NPDA Imports
from project.npda.models import Patient, Transfer
from project.npda.forms.patient_form import PatientForm
from project.npda.forms.external_patient_validators import (
    PatientExternalValidationResult,
)
from project.npda.tests.factories.patient_factory import (
    TODAY,
    VALID_FIELDS,
    VALID_FIELDS_WITH_GP_POSTCODE,
    INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE,
    LOCATION,
)

# Logging
logger = logging.getLogger(__name__)


MOCK_EXTERNAL_VALIDATION_RESULT = PatientExternalValidationResult(
    postcode=VALID_FIELDS["postcode"],
    gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
    gp_practice_postcode=VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"],
    index_of_multiple_deprivation_quintile=INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE,
    location_bng=LOCATION[1],
    location_wgs84=LOCATION[0],
)


def mock_external_validation_result(**kwargs):
    return Mock(
        return_value=dataclasses.replace(MOCK_EXTERNAL_VALIDATION_RESULT, **kwargs)
    )


# We don't want to call remote services in unit tests
@pytest.fixture(autouse=True)
def mock_remote_calls():
    with patch(
        "project.npda.forms.patient_form.validate_patient_sync",
        Mock(return_value=MOCK_EXTERNAL_VALIDATION_RESULT),
    ):
        yield None


@pytest.mark.django_db
def test_create_patient():
    form = PatientForm(VALID_FIELDS)
    assert len(form.errors.as_data()) == 0


@pytest.mark.django_db
def test_create_patient_with_death_date():
    form = PatientForm(
        VALID_FIELDS
        | {"death_date": VALID_FIELDS["diagnosis_date"] + relativedelta(years=1)}
    )

    assert len(form.errors.as_data()) == 0


def test_missing_nhs_number():
    form = PatientForm({})
    assert "nhs_number" in form.errors.as_data()


def test_invalid_nhs_number():
    form = PatientForm({"nhs_number": "123456789"})

    assert "nhs_number" in form.errors.as_data()


def test_date_of_birth_missing():
    form = PatientForm({})
    assert "date_of_birth" in form.errors.as_data()


def test_future_date_of_birth():
    form = PatientForm({"date_of_birth": TODAY + relativedelta(days=1)})

    errors = form.errors.as_data()
    assert "date_of_birth" in errors

    error_message = errors["date_of_birth"][0].messages[0]
    assert error_message == "Cannot be in the future"


def test_over_25():
    form = PatientForm({"date_of_birth": TODAY - relativedelta(years=25, days=1)})

    errors = form.errors.as_data()
    assert "date_of_birth" in errors

    error_message = errors["date_of_birth"][0].messages[0]
    assert error_message == "NPDA patients cannot be 25+ years old. This patient is 25"


def test_missing_diabetes_type():
    form = PatientForm({})
    assert "diabetes_type" in form.errors.as_data()


def test_invalid_diabetes_type():
    form = PatientForm({"diabetes_type": 45})

    assert "diabetes_type" in form.errors.as_data()


def test_missing_diagnosis_date():
    form = PatientForm({})
    assert "diagnosis_date" in form.errors.as_data()


def test_future_diagnosis_date():
    form = PatientForm({"diagnosis_date": TODAY + relativedelta(days=1)})

    errors = form.errors.as_data()
    assert "diagnosis_date" in errors

    error_message = errors["diagnosis_date"][0].messages[0]
    assert error_message == "Cannot be in the future"


def test_diagnosis_date_before_date_of_birth():
    form = PatientForm(
        {
            "date_of_birth": VALID_FIELDS["date_of_birth"],
            "diagnosis_date": VALID_FIELDS["date_of_birth"] - relativedelta(years=1),
        }
    )

    errors = form.errors.as_data()
    assert "diagnosis_date" in errors

    error_message = errors["diagnosis_date"][0].messages[0]
    assert (
        error_message == "'Date of Diabetes Diagnosis' cannot be before 'Date of Birth'"
    )


def test_invalid_sex():
    form = PatientForm({"sex": 45})

    assert "sex" in form.errors.as_data()


def test_invalid_ethnicity():
    form = PatientForm({"ethnicity": 45})

    assert "ethnicity" in form.errors.as_data()


def test_missing_gp_details():
    form = PatientForm({})

    errors = form.errors.as_data()
    assert "gp_practice_ods_code" in errors

    error_message = errors["gp_practice_ods_code"][0].messages[0]
    assert (
        error_message
        == "'GP Practice ODS code' and 'GP Practice postcode' cannot both be empty"
    )


def test_patient_creation_with_future_death_date():
    form = PatientForm({"death_date": TODAY + relativedelta(years=1)})

    errors = form.errors.as_data()
    assert "death_date" in errors

    error_message = errors["death_date"][0].messages[0]
    assert error_message == "Cannot be in the future"


def test_patient_creation_with_death_date_before_date_of_birth():
    form = PatientForm(
        {
            "date_of_birth": VALID_FIELDS["date_of_birth"],
            "death_date": VALID_FIELDS["date_of_birth"] - relativedelta(years=1),
        }
    )

    errors = form.errors.as_data()
    assert "death_date" in errors

    error_message = errors["death_date"][0].messages[0]
    assert error_message == "'Death Date' cannot be before 'Date of Birth'"


def test_multiple_date_validation_errors_returned():
    form = PatientForm(
        {
            "date_of_birth": VALID_FIELDS["date_of_birth"],
            "diagnosis_date": VALID_FIELDS["date_of_birth"] - relativedelta(years=1),
            "death_date": VALID_FIELDS["date_of_birth"] - relativedelta(years=1),
        }
    )

    errors = form.errors.as_data()

    assert "death_date" in errors
    assert "diagnosis_date" in errors


@pytest.mark.django_db
def test_spaces_removed_from_postcode():
    with patch(
        "project.npda.forms.patient_form.validate_patient_sync"
    ) as mock_validate_patient_sync:
        form = PatientForm(
            VALID_FIELDS
            | {
                "postcode": "WC1X 8SH",
            }
        )

        form.is_valid()

        mock_validate_patient_sync.assert_called_once_with(
            postcode="WC1X8SH",
            gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
            gp_practice_postcode=None,
        )


@pytest.mark.django_db
def test_dashes_removed_from_postcode():
    with patch(
        "project.npda.forms.patient_form.validate_patient_sync"
    ) as mock_validate_patient_sync:
        form = PatientForm(
            VALID_FIELDS
            | {
                "postcode": "WC1X-8SH",
            }
        )

        form.is_valid()

        mock_validate_patient_sync.assert_called_once_with(
            postcode="WC1X8SH",
            gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
            gp_practice_postcode=None,
        )


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(postcode="W1A 1AA"),
)
def test_normalised_postcode_saved():
    form = PatientForm(VALID_FIELDS)
    form.is_valid()

    assert form.cleaned_data["postcode"] == "W1A 1AA"


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(postcode=ValidationError("Invalid postcode")),
)
def test_invalid_postcode():
    form = PatientForm(VALID_FIELDS)
    form.is_valid()

    assert "postcode" in form.errors.as_data()


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(postcode=None),
)
def test_error_validating_postcode():
    # TODO MRB: report this back somehow rather than just eat it in the log? (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/334)
    form = PatientForm(VALID_FIELDS)
    form.is_valid()

    assert len(form.errors.as_data()) == 0


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(
        gp_practice_postcode=ValidationError("Invalid postcode")
    ),
)
def test_invalid_gp_postcode():
    form = PatientForm(VALID_FIELDS_WITH_GP_POSTCODE)
    form.is_valid()

    assert "gp_practice_postcode" in form.errors.as_data()


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(gp_practice_postcode=None),
)
def test_error_validating_gp_postcode():
    # TODO MRB: report this back somehow rather than just eat it in the log? (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/334)
    form = PatientForm(VALID_FIELDS_WITH_GP_POSTCODE)
    form.is_valid()

    assert len(form.errors.as_data()) == 0


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(
        gp_practice_ods_code=ValidationError("Invalid ODS code")
    ),
)
def test_invalid_gp_ods_code():
    form = PatientForm(VALID_FIELDS)
    form.is_valid()

    assert "gp_practice_ods_code" in form.errors.as_data()


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(gp_practice_ods_code=None),
)
def test_error_validating_gp_ods_code():
    # TODO MRB: report this back somehow rather than just eat it in the log? (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/334)
    form = PatientForm(VALID_FIELDS)
    form.is_valid()

    assert len(form.errors.as_data()) == 0


@pytest.mark.django_db
def test_lookup_index_of_multiple_deprivation():
    form = PatientForm(VALID_FIELDS)

    form.is_valid()
    assert len(form.errors.as_data()) == 0

    patient = form.save()
    assert (
        patient.index_of_multiple_deprivation_quintile
        == INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE
    )


@pytest.mark.django_db
def test_lookup_location():
    form = PatientForm(VALID_FIELDS)

    form.is_valid()
    assert len(form.errors.as_data()) == 0

    patient = form.save()
    assert patient.location_wgs84 == LOCATION[0]
    assert patient.location_bng == LOCATION[1]


@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(index_of_multiple_deprivation_quintile=None),
)
def test_error_looking_up_index_of_multiple_deprivation():
    # TODO MRB: report this back somehow rather than just eat it in the log? (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/334)
    form = PatientForm(VALID_FIELDS)
    form.is_valid()

    patient = form.save()

    patient.index_of_multiple_deprivation_quintile = None


def test_date_leaving_service_missing():
    # Date leaving service is required if reason leaving service is provided
    form = PatientForm({"reason_leaving_service": 1})
    assert "date_leaving_service" in form.errors.as_data()


def test_date_leaving_service_future():
    form = PatientForm({"date_leaving_service": TODAY + relativedelta(days=1)})

    errors = form.errors.as_data()
    assert "date_leaving_service" in errors

    error_message = errors["date_leaving_service"][0].messages[0]
    assert error_message == "Cannot be in the future"


def test_date_leaving_service_before_diagnosis_date():
    form = PatientForm(
        {
            "diagnosis_date": VALID_FIELDS["diagnosis_date"],
            "date_leaving_service": VALID_FIELDS["diagnosis_date"]
            - relativedelta(years=1),
        }
    )

    errors = form.errors.as_data()
    assert "date_leaving_service" in errors

    error_message = errors["date_leaving_service"][0].messages[0]
    assert (
        error_message
        == "'Date Leaving Service' cannot be before 'Date of Diabetes Diagnosis'"
    )


def test_date_leaving_service_before_date_of_birth():
    form = PatientForm(
        {
            "date_of_birth": VALID_FIELDS["date_of_birth"],
            "date_leaving_service": VALID_FIELDS["date_of_birth"]
            - relativedelta(years=1),
        }
    )

    errors = form.errors.as_data()
    assert "date_leaving_service" in errors

    error_message = errors["date_leaving_service"][0].messages[0]
    assert error_message == "'Date Leaving Service' cannot be before 'Date of Birth'"


def test_reason_leaving_service_missing():
    # Reason leaving service is required if date leaving service is provided
    form = PatientForm({"date_leaving_service": TODAY})
    assert "reason_leaving_service" in form.errors.as_data()


def test_reason_leaving_service_invalid():
    form = PatientForm({"reason_leaving_service": 99})
    assert "reason_leaving_service" in form.errors.as_data()


@skip("This test is failing")
@pytest.mark.django_db
@patch(
    "project.npda.forms.patient_form.validate_patient_sync",
    mock_external_validation_result(index_of_multiple_deprivation_quintile=None),
)
def test_successful_patient_transfer():
    # Create patient
    patient = Patient.objects.create(**VALID_FIELDS)

    # Update patient
    form = PatientForm(
        VALID_FIELDS | {"reason_leaving_service": 1, "date_leaving_service": TODAY},
        instance=patient,
    )

    patient = form.save()

    transfer = Transfer.objects.get(patient=patient)

    assert len(form.errors.as_data()) == 0
    assert form.is_valid()
    # assert form.save().date_leaving_service == TODAY
    # assert form.save().reason_leaving_service == 1
    assert transfer.patient == patient
    assert transfer.date_leaving_service == TODAY
    assert transfer.reason_leaving_service == 1
