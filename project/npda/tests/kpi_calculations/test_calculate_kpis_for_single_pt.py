import logging
from datetime import date
from dateutil.relativedelta import relativedelta

import pytest

from project.constants.hba1c_format import HBA1C_FORMATS
from project.constants.retinal_screening_results import (
    RETINAL_SCREENING_RESULTS,
)
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


@pytest.mark.parametrize(
    "gte_12yo, pass_kpi_25, pass_kpi_26, pass_kpi_27, pass_kpi_28, pass_kpi_29, pass_kpi_30, pass_kpi_31",
    [
        (True, True, True, True, True, True, True, True),
        (True, False, False, False, False, False, False, False),
        (False, True, False, False, None, None, None, None),
    ],
)
@pytest.mark.django_db
def test_calculate_kpis_for_patient_returns_correct_results(
    AUDIT_START_DATE,
    gte_12yo,
    pass_kpi_25,
    pass_kpi_26,
    pass_kpi_27,
    pass_kpi_28,
    pass_kpi_29,
    pass_kpi_30,
    pass_kpi_31,
):
    """Tests that the `calculate_kpis_for_single_patient()` method
    returns the expected results.
    """

    # Gather
    expected_kpi_results = (
        pass_kpi_25,
        pass_kpi_26,
        pass_kpi_27,
        pass_kpi_28,
        pass_kpi_29,
        pass_kpi_30,
        pass_kpi_31,
    )

    # Initilise defaults
    date_of_birth = AUDIT_START_DATE - relativedelta(years=10)
    visit_date = {}
    kpi_25_visit_values = {}
    kpi_26_visit_values = {}
    kpi_27_visit_values = {}
    kpi_28_visit_values = {}
    kpi_29_visit_values = {}
    kpi_30_visit_values = {}
    kpi_31_visit_values = {}

    # Set the KPI visit values based on the pass_kpi_XX parameters
    OBSERVATION_DATE_IF_PASSED = AUDIT_START_DATE + relativedelta(days=2)
    if any(expected_kpi_results):
        visit_date = {
            "visit__visit_date": OBSERVATION_DATE_IF_PASSED,
        }
    if pass_kpi_25:
        kpi_25_visit_values = {
            "visit__hba1c": 46,
            "visit__hba1c_format": HBA1C_FORMATS[0][0],
            "visit__hba1c_date": OBSERVATION_DATE_IF_PASSED,
        }
    if pass_kpi_26:
        kpi_26_visit_values = {
            "visit__height": 140.0,
            "visit__weight": 40.0,
            "visit__height_weight_observation_date": OBSERVATION_DATE_IF_PASSED,
        }
    if pass_kpi_27:
        kpi_27_visit_values = {
            "visit__thyroid_function_date": OBSERVATION_DATE_IF_PASSED,
        }

    if gte_12yo:
        date_of_birth = AUDIT_START_DATE - relativedelta(years=12)

        if pass_kpi_28:
            kpi_28_visit_values = {
                "visit__systolic_blood_pressure": 130,
                "visit__blood_pressure_observation_date": AUDIT_START_DATE
                + relativedelta(days=5),
            }
        if pass_kpi_29:
            kpi_29_visit_values = {
                "visit__albumin_creatinine_ratio": 2,
                "visit__albumin_creatinine_ratio_date": AUDIT_START_DATE
                + relativedelta(days=2),
            }
        if pass_kpi_30:
            kpi_30_visit_values = {
                "visit__retinal_screening_result": RETINAL_SCREENING_RESULTS[0][0],
                "visit__retinal_screening_observation_date": AUDIT_START_DATE,
            }
        if pass_kpi_31:
            kpi_31_visit_values = {
                "visit__foot_examination_observation_date": AUDIT_START_DATE,
            }



    # Create Patient with Visit
    mock_pt = PatientFactory(
        date_of_birth=date_of_birth,
        **visit_date,
        **kpi_25_visit_values,
        **kpi_26_visit_values,
        **kpi_27_visit_values,
        **kpi_28_visit_values,
        **kpi_29_visit_values,
        **kpi_30_visit_values,
        **kpi_31_visit_values,
    )
    mock_pt_pdu = (
        mock_pt.paediatric_diabetes_units.first().paediatric_diabetes_unit
    )

    # Init the KPI calculator
    kpi_calculator = CalculateKPIS(calculation_date=AUDIT_START_DATE)
    kpi_calc_obj = kpi_calculator.calculate_kpis_for_single_patient(
        mock_pt,
        mock_pt_pdu,
    )

    # Check characteristics
    assert kpi_calc_obj["audit_start_date"] == AUDIT_START_DATE
    assert kpi_calc_obj["gte_12yo"] == gte_12yo

    # Check the KPI results
    kpi_results = kpi_calc_obj["kpi_results"]

    keys = [
        "kpi_25_hba1c",
        "kpi_26_bmi",
        "kpi_27_thyroid_screen",
        "kpi_28_blood_pressure",
        "kpi_29_urinary_albumin",
        "kpi_30_retinal_screening",
        "kpi_31_foot_examination",
    ]
    for key, expected_result in zip(keys, expected_kpi_results):
        assert (
            kpi_results[key] == expected_result
        ), f"Expected {key} to be {expected_result}, but got {kpi_results[key]}"
