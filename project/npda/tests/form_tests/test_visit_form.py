import dataclasses
from decimal import Decimal

import pytest
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError

from project.npda.forms.visit_form import VisitForm
from project.npda.forms.external_visit_validators import VisitExternalValidationResult, CentileAndSDS
from project.npda.tests.factories.patient_factory import PatientFactory


MOCK_EXTERNAL_VALIDATION_RESULT = VisitExternalValidationResult(None, None, None, None)

def mock_external_validation_result(**kwargs):
    return Mock(return_value=dataclasses.replace(MOCK_EXTERNAL_VALIDATION_RESULT, **kwargs))

# We don't want to call remote services in unit tests
@pytest.fixture(autouse=True)
def mock_remote_calls():
    with patch("project.npda.forms.visit_form.validate_visit_sync", Mock(return_value=MOCK_EXTERNAL_VALIDATION_RESULT)):
        yield None


# https://github.com/rcpch/national-paediatric-diabetes-audit/issues/359
@pytest.mark.django_db
def test_height_and_weight_set_correctly():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
        },
        initial = {
            "patient": patient
        }
    )

    # Not passing all the data so it will have errors, just trigger the cleaners
    form.is_valid()

    assert form.cleaned_data["height"] == 60
    assert form.cleaned_data["weight"] == 50


@pytest.mark.django_db
@patch("project.npda.forms.visit_form.validate_visit_sync", mock_external_validation_result(
    height_result=CentileAndSDS(centile=Decimal("0.1"), sds=Decimal("0.2")),
    weight_result=CentileAndSDS(centile=Decimal("0.3"), sds=Decimal("0.4")),
    bmi=Decimal("0.5"),
    bmi_result=CentileAndSDS(centile=Decimal("0.6"), sds=Decimal("0.7")),
))
def test_dgc_results_saved():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
        },
        initial = {
            "patient": patient
        }
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
@patch("project.npda.forms.visit_form.validate_visit_sync", mock_external_validation_result(
    height_result=CentileAndSDS(centile=Decimal("0.1"), sds=Decimal("0.2")),
))
def test_partial_dgc_results_saved():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
        },
        initial = {
            "patient": patient
        }
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
@patch("project.npda.forms.visit_form.validate_visit_sync", mock_external_validation_result(
    height_result=ValidationError("oh noes!")
))
def test_dgc_height_validation_error():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
        },
        initial = {
            "patient": patient
        }
    )

    # Trigger the cleaners
    form.is_valid()

    assert form.errors["height"] == ["oh noes!"]


@pytest.mark.django_db
@patch("project.npda.forms.visit_form.validate_visit_sync", mock_external_validation_result(
    weight_result=ValidationError("oh noes!")
))
def test_dgc_weight_validation_error():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
        },
        initial = {
            "patient": patient
        }
    )

    # Trigger the cleaners
    form.is_valid()

    assert form.errors["weight"] == ["oh noes!"]


@pytest.mark.django_db
@patch("project.npda.forms.visit_form.validate_visit_sync", mock_external_validation_result(
    bmi_result=ValidationError("oh noes!")
))
def test_dgc_bmi_validation_error():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "60",
            "weight": "50",
        },
        initial = {
            "patient": patient
        }
    )

    # Trigger the cleaners
    form.is_valid()

    assert form.errors["height"] == ["oh noes!"]
    assert form.errors["weight"] == ["oh noes!"]
