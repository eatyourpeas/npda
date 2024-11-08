import pytest

from project.npda.forms.visit_form import VisitForm
from project.npda.tests.factories.patient_factory import PatientFactory

# https://github.com/rcpch/national-paediatric-diabetes-audit/issues/359
@pytest.mark.django_db
def test_height_and_weight_set_correctly():
    patient = PatientFactory()

    form = VisitForm(
        data={
            "height": "1.5",
            "weight": "50",
        },
        initial = {
            "patient": patient
        }
    )
    assert form.is_valid()
    assert form.cleaned_data["height"] == 1.5
    assert form.cleaned_data["weight"] == 50