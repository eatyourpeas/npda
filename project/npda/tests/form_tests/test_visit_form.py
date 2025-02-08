import dataclasses
from decimal import Decimal

import pytest
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError

from project.npda.forms.visit_form import VisitForm
from project.npda.forms.external_visit_validators import (
    VisitExternalValidationResult,
    CentileAndSDS,
)
from project.npda.tests.factories.patient_factory import PatientFactory


MOCK_EXTERNAL_VALIDATION_RESULT = VisitExternalValidationResult(None, None, None, None)


def mock_external_validation_result(**kwargs):
    return Mock(
        return_value=dataclasses.replace(MOCK_EXTERNAL_VALIDATION_RESULT, **kwargs)
    )


# We don't want to call remote services in unit tests
@pytest.fixture(autouse=True)
def mock_remote_calls():
    with patch(
        "project.npda.forms.visit_form.validate_visit_sync",
        Mock(return_value=MOCK_EXTERNAL_VALIDATION_RESULT),
    ):
        yield None


# https://github.com/rcpch/national-paediatric-diabetes-audit/issues/359
@pytest.mark.django_db
def test_height_and_weight_set_correctly():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
            "height_weight_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )

    # Not passing all the data so it will have errors, just trigger the cleaners
    form.is_valid()

    assert form.cleaned_data["height"] == 60
    assert form.cleaned_data["weight"] == 50


@pytest.mark.django_db
def test_height_and_weight_missing_values():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": None,
            "weight": None,
            "height_weight_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )

    # Not passing all the data so it will have errors, just trigger the cleaners
    assert form.is_valid() == False, f"Height/Weight not supplied but date supplied"


@pytest.mark.django_db
def test_height_and_weight_missing_date():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": None,
            "height_weight_observation_date": None,
        },
        initial={"patient": patient},
    )

    # Not passing all the data so it will have errors, just trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Height/Weight observation date not supplied but height/weight supplied"


@pytest.mark.django_db
@patch(
    "project.npda.forms.visit_form.validate_visit_sync",
    mock_external_validation_result(
        height_result=CentileAndSDS(centile=Decimal("0.1"), sds=Decimal("0.2")),
        weight_result=CentileAndSDS(centile=Decimal("0.3"), sds=Decimal("0.4")),
        bmi=Decimal("0.5"),
        bmi_result=CentileAndSDS(centile=Decimal("0.6"), sds=Decimal("0.7")),
    ),
)
def test_dgc_results_saved():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
            "height_weight_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )

    # Trigger the cleaners
    form.is_valid()

    # TODO MRB: why do I have to do this in test but it happens automatically normally?
    form.instance.patient_id = patient.id
    visit = form.save()

    assert visit.height_centile == Decimal("0.1")
    assert visit.height_sds == Decimal("0.2")
    assert visit.weight_centile == Decimal("0.3")
    assert visit.weight_sds == Decimal("0.4")
    assert visit.bmi == Decimal("0.5")
    assert visit.bmi_centile == Decimal("0.6")
    assert visit.bmi_sds == Decimal("0.7")


@pytest.mark.django_db
@patch(
    "project.npda.forms.visit_form.validate_visit_sync",
    mock_external_validation_result(
        height_result=CentileAndSDS(centile=Decimal("0.1"), sds=Decimal("0.2")),
    ),
)
def test_partial_dgc_results_saved():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
            "height_weight_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )

    # Trigger the cleaners
    form.is_valid()

    # TODO MRB: why do I have to do this in test but it happens automatically normally?
    form.instance.patient_id = patient.id
    visit = form.save()

    assert visit.height_centile == Decimal("0.1")
    assert visit.height_sds == Decimal("0.2")
    assert visit.weight_centile is None
    assert visit.weight_sds is None
    assert visit.bmi is None
    assert visit.bmi_centile is None
    assert visit.bmi_sds is None


@pytest.mark.django_db
@patch(
    "project.npda.forms.visit_form.validate_visit_sync",
    mock_external_validation_result(height_result=ValidationError("oh noes!")),
)
def test_dgc_height_validation_error():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
            "height_weight_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )

    # Trigger the cleaners
    form.is_valid()

    assert form.errors["height"] == ["oh noes!"]


@pytest.mark.django_db
@patch(
    "project.npda.forms.visit_form.validate_visit_sync",
    mock_external_validation_result(weight_result=ValidationError("oh noes!")),
)
def test_dgc_weight_validation_error():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
            "height_weight_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )

    # Trigger the cleaners
    form.is_valid()

    assert form.errors["weight"] == ["oh noes!"]


@pytest.mark.django_db
@patch(
    "project.npda.forms.visit_form.validate_visit_sync",
    mock_external_validation_result(bmi_result=ValidationError("oh noes!")),
)
def test_dgc_bmi_validation_error():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
            "height_weight_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )

    # Trigger the cleaners
    form.is_valid()

    assert form.errors["height"] == ["oh noes!"]
    assert form.errors["weight"] == ["oh noes!"]


"""
HbA1c tests
"""


@pytest.mark.django_db
def test_hba1c_value_ifcc_less_than_20_form_fail_validation():
    """
    Test that HbA1c value (IFCC mmol/mol) less than 20 % fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": "2",
            "hba1c_format": "2",  # IFCC (mmol/mol)
            "hba1c_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    form.is_valid()

    assert "hba1c" in form.errors


@pytest.mark.django_db
def test_hba1c_value_dcct_less_than_20_form_pass_validation():
    """
    Test that HbA1c value (DCCT %) less than 20 % is accepted
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": "5",
            "hba1c_format": "2",  # DCCT (%)
            "hba1c_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert form.is_valid(), f"Form should be valid but got {form.errors}"


@pytest.mark.django_db
def test_hba1c_value_ifcc_more_than_195_form_validation():
    """
    Test that HbA1c value (IFCC mmol/mo) > 195 mmol/mol fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": "200",
            "hba1c_format": "1",  # IFCC (mmol/mol)
            "hba1c_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should not be valid when hba1c > 195 mmol/mol"
    assert "hba1c" in form.errors


@pytest.mark.django_db
def test_hba1c_value_dcct_more_than_20_form_fails_validation():
    """
    Test that HbA1c value (DCCT %) more than 20 fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": "25",
            "hba1c_format": "2",  # DCCT (%)
            "hba1c_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert form.is_valid() == False, f"Form should be not valid when hba1c > 20%"
    assert "hba1c" in form.errors


@pytest.mark.django_db
def test_hba1c_value_dcct_less_than_3_form_fails_validation():
    """
    Test that HbA1c value (DCCT %) < 3% fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": "2",
            "hba1c_format": "2",  # DCCT (%)
            "hba1c_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert form.is_valid() == False, f"Form should not be valid when hba1c < 3%"
    assert "hba1c" in form.errors


@pytest.mark.django_db
def test_hba1c_missing_form_fails_validation():
    """
    Test that HbA1c value (DCCT %) < 3% fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": None,
            "hba1c_format": "2",  # DCCT (%)
            "hba1c_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert form.is_valid() == False, f"Form should not be valid when HbA1c is missing"
    assert "hba1c" in form.errors


@pytest.mark.django_db
def test_hba1c_date_missing_form_fails_validation():
    """
    Test that HbA1c value (DCCT %) missing fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": 5,
            "hba1c_format": "2",  # DCCT (%)
            "hba1c_date": None,
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should not be valid when HbA1c date is missing"
    assert "hba1c_date" in form.errors


@pytest.mark.django_db
def test_hba1c_date_and_hba1c_format_missing_form_fails_validation():
    """
    Test that HbA1c format and date missing fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": 5,
            "hba1c_format": None,  # DCCT (%)
            "hba1c_date": None,
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should not be valid when HbA1c date and format are missing"
    assert "hba1c_date" in form.errors
    assert "hba1c_format" in form.errors


@pytest.mark.django_db
def test_hba1c_date_and_hba1c_format_hba1c_all_missing_form_passes_validation():
    """
    Test that HbA1c format and date missing fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "hba1c": None,
            "hba1c_format": None,  # DCCT (%)
            "hba1c_date": None,
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == True
    ), f"Form should  be valid when HbA1c, HbA1c date and format are missing, but got {form.errors}"
    assert "hba1c_date" not in form.errors
    assert "hba1c_format" not in form.errors
    assert "hba1c" not in form.errors


"""
Diabetes treatment tests
"""


@pytest.mark.django_db
def test_treatment_closed_loop_form_passes_validation():
    """
    Test that both pump and closed loop system are accepted
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "treatment": "3",  # Insulin pump
            "closed_loop_system": "1",  # Closed loop system (licenced)
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert form.is_valid(), f"Form should be valid but got {form.errors}"


@pytest.mark.django_db
def test_treatment_missing_closed_loop_form_fails_validation():
    """
    Test that both closed loop system selected but treatment is None fail validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "treatment": None,
            "closed_loop_system": "1",  # Closed loop system (licenced)
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as closed loop system selected but treatment not selected as 1 or 3 (pump or pump + meds)"


@pytest.mark.django_db
def test_treatment_mdi_but_closed_loop_selected_form_fails_validation():
    """
    Test that MDI selected but closed loop system is also selected
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "treatment": 2,  # MDI
            "closed_loop_system": "1",  # Closed loop system (licenced)
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as closed loop system selected but treatment not selected as 1 or 3 (pump or pump + meds)"


"""
Blood pressure tests
"""


@pytest.mark.django_db
def test_blood_pressure_values_form_passes_validation():
    """
    Test that both systolic and diastolic blood pressure values are accepted
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "systolic_blood_pressure": "120",
            "diastolic_blood_pressure": "80",
            "blood_pressure_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert form.is_valid(), f"Form should be valid but got {form.errors}"


@pytest.mark.django_db
def test_blood_pressure_missing_values_form_fails_validation():
    """
    Test that one missing systolic blood pressure value fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "systolic_blood_pressure": None,
            "diastolic_blood_pressure": "80",
            "blood_pressure_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as missing systolic blood pressure but passed measure."


@pytest.mark.django_db
def test_blood_pressure_missing_date_form_fails_validation():
    """
    Test that missing blood pressure observation date fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "systolic_blood_pressure": "120",
            "diastolic_blood_pressure": "80",
            "blood_pressure_observation_date": None,
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as missing blood pressure date but passed measure."


@pytest.mark.django_db
def test_systolic_blood_pressure_over_240_form_fails_validation():
    """
    Test that systolic blood pressure value > 240 fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "systolic_blood_pressure": "250",
            "diastolic_blood_pressure": "80",
            "blood_pressure_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as systolic blood pressure > 240 and is a medical emergency, but passed measure."


@pytest.mark.django_db
def test_systolic_blood_pressure_below_80_form_fails_validation():
    """
    Test that systolic blood pressure value < 80 fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "systolic_blood_pressure": "60",
            "diastolic_blood_pressure": "80",
            "blood_pressure_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as systolic blood pressure < 80 and tbh not really compatible with life, but passed measure."


@pytest.mark.django_db
def test_diastolic_blood_pressure_over_120_form_fails_validation():
    """
    Test that diastolic blood pressure value > 120 fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "systolic_blood_pressure": "120",
            "diastolic_blood_pressure": "125",
            "blood_pressure_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as diastolic blood pressure > 120 and is a medical emergency, but passed measure."


@pytest.mark.django_db
def test_diastolic_blood_pressure_below_20_form_fails_validation():
    """
    Test that diastolic blood pressure value < 20 fails validation
    """
    patient = PatientFactory()

    form = VisitForm(
        data={
            "systolic_blood_pressure": "120",
            "diastolic_blood_pressure": "15",
            "blood_pressure_observation_date": "2025-01-01",
        },
        initial={"patient": patient},
    )
    # Trigger the cleaners
    assert (
        form.is_valid() == False
    ), f"Form should be invalid as diastolic blood pressure < 20, but passed measure."
