import logging
from datetime import date


import pytest

from project.npda.kpi_class.kpis import CalculateKPIS
from project.npda.models.patient import Patient
from project.npda.tests.factories.patient_factory import PatientFactory


@pytest.mark.django_db
def test_ensure_calculate_kpis_for_patient_returns_correct_kpi_subset(
    AUDIT_START_DATE,
):
    """Tests that the `calculate_kpis_for_single_patient()` method
    returns the correct subset of KPIs for a single patient.
    """
    kpi_calculator = CalculateKPIS(calculation_date=AUDIT_START_DATE)
    mock_pt = PatientFactory()
    mock_pt_pdu = (
        mock_pt.paediatric_diabetes_units.first().paediatric_diabetes_unit
    )
    kpi_calc_obj = kpi_calculator.calculate_kpis_for_single_patient(
        mock_pt,
        mock_pt_pdu,
    )

    breakpoint()
    kpi_results_obj = kpi_calc_obj["kpi_results"].keys()

    # Check that the KPIs are a subset of the full KPI list
    EXPECTED_KPIS_SUBSET = list(range(25, 32))
    EXPECTED_KPI_KEYS = [
        kpi_calculator.kpi_name_registry.get_attribute_name(i)
        for i in EXPECTED_KPIS_SUBSET
    ]

    for expected_kpi_key in EXPECTED_KPI_KEYS:
        assert (
            expected_kpi_key in kpi_results_obj
        ), f"Expected KPI {expected_kpi_key} in single patient subset, but not present in results"
