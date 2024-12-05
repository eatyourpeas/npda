import pytest
from unittest.mock import Mock, patch

from project.npda.forms.visit_form import VisitForm
from project.npda.forms.external_visit_validators import VisitExternalValidationResult
from project.npda.tests.factories.patient_factory import PatientFactory


MOCK_EXTERNAL_VALIDATION_RESULT = VisitExternalValidationResult(None, None, None, None, None, None, None)

def mock_external_validation_result(**kwargs):
    return Mock(return_value=dataclasses.replace(MOCK_EXTERNAL_VALIDATION_RESULT, **kwargs))

# We don't want to call remote services in unit tests
@pytest.fixture(autouse=True)
def mock_remote_calls():
    with patch("project.npda.forms.patient_form.validate_patient_sync", Mock(return_value=MOCK_EXTERNAL_VALIDATION_RESULT)):
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

