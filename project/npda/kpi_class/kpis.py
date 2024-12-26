"""Views for KPIs calculations
"""

from collections import defaultdict
import logging
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta

# Python imports
from decimal import Decimal
from pprint import pformat
from typing import Any, Dict, Optional, Tuple, Union

from dateutil.relativedelta import relativedelta

# Django imports
from django.apps import apps
from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    Func,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    When,
)

# NPDA Imports
from project.constants import diabetes_types
from project.constants.albuminuria_stage import ALBUMINURIA_STAGES
from project.constants.diabetes_types import DIABETES_TYPES
from project.constants.hospital_admission_reasons import (
    HOSPITAL_ADMISSION_REASONS,
)
from project.constants.retinal_screening_results import (
    RETINAL_SCREENING_RESULTS,
)
from project.constants.smoking_status import SMOKING_STATUS
from project.constants.types.kpi_types import (
    IndividualPtKPICalculationsDict,
    IndividualPtKPICalculationsObject,
    IndividualPtKPIResults,
    KPICalculationsObject,
    KPIResult,
    kpi_registry,
)
from project.constants.yes_no_unknown import YES_NO_UNKNOWN
from project.npda.general_functions import get_audit_period_for_date
from project.npda.models import Patient, Visit
from project.npda.models.paediatric_diabetes_unit import PaediatricDiabetesUnit
from project.npda.models.transfer import Transfer

# Logging
logger = logging.getLogger(__name__)


class CalculateKPIS:
    """
    Calculates KPIs
    """

    def __init__(
        self,
        calculation_date: date = None,
        return_pt_querysets: bool = False,
    ):
        """Calculates KPIs for given pz_code

        Initialise with:
            * calculation_date (date) - used to define start and end date of
            audit period
            * return_pt_querysets (bool) - if True, will return the querysets
            of patients for each kpi calculation

        Exposes methods:
            1) calculate_kpis_for_patients (QuerySet[Patient])
                - Calculate KPIs for given patients.
            2) calculate_kpis_for_pdus (list[str])
                - Calculate KPIs for given PZ codes.
            3) calculate_kpis_for_single_patient (Patient)
                - Calculate KPIs for a single patient.

            Each calculation method works to set the `self.patients` and
            `self.total_patients_count` attributes used throughout all
            calculations.

            Both methods return a KPICalculationsObject dataclass instance,
            containing all KPIAggregation results.

        Exposes attributes:
            * kpi_name_registry (KPINameRegistry) - used to get the kpi method name / label from
            the kpi number
        """

        # Set various attributes used in calculations
        self.calculation_date = calculation_date if calculation_date is not None else date.today()
        # Set the start and end audit dates
        self.audit_start_date, self.audit_end_date = self._get_audit_start_and_end_dates()
        self.AUDIT_DATE_RANGE = (self.audit_start_date, self.audit_end_date)

        # Set the return_pt_querysets attribute
        self.return_pt_querysets = return_pt_querysets

        # Sets the KPI attribute names map
        self.kpi_name_registry = kpi_registry

    def calculate_kpis_for_patients(
        self,
        patients: QuerySet[Patient],
    ) -> KPICalculationsObject:
        """Calculate KPIs 1 - 49 for given patients and cohort range
        (self.audit_start_date and self.audit_end_date).

        Params:
            * patients (QuerySet[Patient]) - Queryset of patients
            for KPI calculations and aggregations.
        """

        self.patients = patients
        self.total_patients_count = self.patients.count()

        return self._calculate_kpis()

    def calculate_kpis_for_pdus(
        self,
        pz_codes: list[str],
    ) -> KPICalculationsObject:
        """Calculate KPIs 1 - 49 for given pz_codes and cohort range
        (self.audit_start_date and self.audit_end_date).

        Params:
            * pz_codes (list[str]) - List of PZ codes used to filter patients
            for KPI calculations and aggregations."""

        self.patients = Patient.objects.filter(
            paediatric_diabetes_units__paediatric_diabetes_unit__pz_code__in=pz_codes
        )
        self.total_patients_count = self.patients.count()

        return self._calculate_kpis()

    def calculate_kpis_for_single_patient(
        self,
        patient: Patient,
        pdu: PaediatricDiabetesUnit,
    ) -> IndividualPtKPICalculationsDict:
        """Calculate relevant KPIs subset for a single patient.

        Params:
            * patient (Patient) - Single patient for KPI calculations and aggregations.
            * pdu (PaediatricDiabetesUnit) - PDU for the patient. Used to filter transfer

        Returns:
            * dict - looks like IndividualPtKPICalculationsObject

            Example:
            {
                "calculation_datetime": datetime.datetime(
                    2024, 11, 15, 9, 49, 32, 684190
                ),
                "audit_start_date": datetime.date(2024, 4, 1),
                "audit_end_date": datetime.date(2025, 3, 31),
                "gte_12yo": False,
                "diagnosed_in_period": False,
                "died_in_period": False,
                "transfer_in_period": False,
                "kpi_results": {
                    "kpi_25_hba1c": False,
                    "kpi_26_bmi": False,
                    "kpi_27_thyroid_screen": False,
                    "kpi_28_blood_pressure": None,
                    "kpi_29_urinary_albumin": None,
                    "kpi_30_retinal_screening": None,
                    "kpi_31_foot_examination": None,
                },
                "total_passed": 0,
                "expected_total": 3,
            }
        """

        if type(patient) != Patient:
            raise ValueError(f"patient must be a Patient instance, got {type(patient)}")
        if type(pdu) != PaediatricDiabetesUnit:
            raise ValueError(f"pdu must be a PaediatricDiabetesUnit instance, got {type(pdu)}")

        # Get values that are simple look ups
        calculation_datetime = datetime.now()
        audit_start_date = self.audit_start_date
        audit_end_date = self.audit_end_date
        gte_12yo = patient.date_of_birth <= calculation_datetime.date() - relativedelta(years=12)
        diagnosed_in_period = patient.diagnosis_date in self.AUDIT_DATE_RANGE
        died_in_period = patient.death_date in self.AUDIT_DATE_RANGE
        transfer_in_period = (
            Transfer.objects.get(
                patient=patient,
                paediatric_diabetes_unit=pdu,
            ).date_leaving_service
            is not None
        )

        # Now get IndividualPtKPIResults

        # Set the base Visit attributes
        base_visits: QuerySet[Visit] = patient.visit_set.filter(
            visit_date__range=(self.AUDIT_DATE_RANGE)
        )
        passed_kpi_25_hba1c = base_visits.filter(
            Q(hba1c__isnull=False),
            Q(hba1c_date__range=(self.AUDIT_DATE_RANGE)),
        ).exists()
        passed_kpi_26_bmi = base_visits.filter(
            Q(height__isnull=False),
            Q(weight__isnull=False),
            # Within audit period
            Q(height_weight_observation_date__range=(self.AUDIT_DATE_RANGE)),
        ).exists()
        passed_kpi_27_thyroid_screen = base_visits.filter(
            # Within audit period
            Q(thyroid_function_date__range=(self.AUDIT_DATE_RANGE)),
        ).exists()

        # Only for pts >= 12yo
        passed_kpi_28_blood_pressure = None
        passed_kpi_29_urinary_albumin = None
        passed_kpi_30_retinal_screening = None
        passed_kpi_31_foot_examination = None
        if gte_12yo:
            passed_kpi_28_blood_pressure = base_visits.filter(
                # Within audit period
                Q(systolic_blood_pressure__isnull=False),
                Q(blood_pressure_observation_date__range=(self.AUDIT_DATE_RANGE)),
            ).exists()
            passed_kpi_29_urinary_albumin = base_visits.filter(
                Q(albumin_creatinine_ratio__isnull=False),
                # Within audit period
                Q(albumin_creatinine_ratio_date__range=(self.AUDIT_DATE_RANGE)),
            ).exists()
            passed_kpi_30_retinal_screening = base_visits.filter(
                Q(
                    retinal_screening_result__in=[
                        RETINAL_SCREENING_RESULTS[0][0],
                        RETINAL_SCREENING_RESULTS[1][0],
                    ]
                ),
                # Within audit period
                Q(retinal_screening_observation_date__range=(self.AUDIT_DATE_RANGE)),
            ).exists()
            passed_kpi_31_foot_examination = base_visits.filter(
                # Within audit period
                Q(foot_examination_observation_date__range=(self.AUDIT_DATE_RANGE)),
            ).exists()

        # Initiliase the calculations IndividualPtKPICalculationsObject
        pt_kpi_results = IndividualPtKPIResults(
            kpi_25_hba1c=passed_kpi_25_hba1c,
            kpi_26_bmi=passed_kpi_26_bmi,
            kpi_27_thyroid_screen=passed_kpi_27_thyroid_screen,
            kpi_28_blood_pressure=passed_kpi_28_blood_pressure,
            kpi_29_urinary_albumin=passed_kpi_29_urinary_albumin,
            kpi_30_retinal_screening=passed_kpi_30_retinal_screening,
            kpi_31_foot_examination=passed_kpi_31_foot_examination,
        )

        # Initialise the calculations IndividualPtKPICalculationsObject
        # At the end we convert to dict for serialization
        return_obj = IndividualPtKPICalculationsObject(
            calculation_datetime=calculation_datetime,
            audit_start_date=audit_start_date,
            audit_end_date=audit_end_date,
            gte_12yo=gte_12yo,
            diagnosed_in_period=diagnosed_in_period,
            died_in_period=died_in_period,
            transfer_in_period=transfer_in_period,
            kpi_results=pt_kpi_results,
        )

        return asdict(return_obj)

    def _calculate_kpis(
        self,
    ) -> KPICalculationsObject:
        """Calculate KPIs 1 - 49 for set self.patients and cohort range
        (self.audit_start_date and self.audit_end_date).

        We dynamically set these attributes using names set in self.kpis, done
        in the self._get_kpi_attribute_names method during object init.

        Incrementally build the query, which will be executed in a single
        transaction once a value is evaluated.
        """
        # Init dict to store calc results
        calculated_kpis = {}

        # Standard KPIs plus 32 which has 3 sub KPIs
        kpi_idxs = list(range(1, 32)) + [321, 322, 323] + (list(range(33, 50)))

        for i in kpi_idxs:
            # Dynamically get the method name from the kpis_names_map
            kpi_method_name = self.kpi_name_registry.get_attribute_name(i)

            kpi_result = self._run_kpi_calculation_method(kpi_method_name)

            # Each kpi method returns a KPIResult object
            # so we convert it first to a dictionary
            calculated_kpis[kpi_method_name] = asdict(kpi_result)

        # Add in used attributes for calculations
        return_obj = {}
        return_obj["calculation_datetime"] = datetime.now()
        return_obj["audit_start_date"] = self.audit_start_date
        return_obj["audit_end_date"] = self.audit_end_date
        return_obj["total_patients_count"] = self.total_patients_count

        # Finally, add in the kpis
        return_obj["calculated_kpi_values"] = {}

        for kpi_name, kpi_result in calculated_kpis.items():

            # First assign the kpi_name : kpi_result
            return_obj["calculated_kpi_values"][kpi_name] = kpi_result

            # Then we need to get the rendered KPI label, based on the kpi
            # number.
            # Split the kpi_name which includes
            # kpi_idx (and sub-idx if KPI32)
            name_split: list[str] = kpi_name.split("_")

            kpi_number = int(name_split[1])

            # If KPI32, offset to get sub-index
            if kpi_number == 32:
                kpi_number = 320 + int(name_split[2])

            # Assign the KPI label
            return_obj["calculated_kpi_values"][kpi_name]["kpi_label"] = self._get_kpi_label(
                kpi_number
            )

        return return_obj

    def _get_audit_start_and_end_dates(self) -> tuple[date, date]:
        return get_audit_period_for_date(input_date=self.calculation_date)

    def _get_kpi_label(self, kpi_number: int) -> str:
        """Returns a readable title for a given KPI number"""

        return kpi_registry.get_rendered_label(kpi_number)

    def _run_kpi_calculation_method(self, kpi_method_name: str) -> Union[KPIResult | str]:
        """Will find and run kpi calculation method
        (name schema is calculation_KPI_NAME_MAP_VALUE)
        """

        kpi_method = getattr(self, f"calculate_{kpi_method_name}", None)

        kpi_result = kpi_method()

        # Validations
        if not is_dataclass(kpi_result):
            raise TypeError(
                f"kpi_result is not a dataclass instance: {kpi_result} (type: {type(kpi_result)})"
            )
        if not isinstance(kpi_result, KPIResult):
            raise TypeError(
                f"kpi_result is not an instance of KPIResult: {kpi_result} (type: {type(kpi_result)})"
            )

        return kpi_result

    def _get_pt_querysets_object(
        self,
        eligible: QuerySet[Patient],
        passed: QuerySet[Patient],
        ineligible: Optional[QuerySet[Patient]] = None,
        failed: Optional[QuerySet[Patient]] = None,
    ) -> Optional[dict[str, QuerySet[Patient]]]:
        """Helper method to get a dictionary of querysets for patients.

        if `self.return_pt_querysets` is False, will return None

        NOTE:
            - eligible and passed are required
            - ineligible if not provided is found from filtering out eligible
                patients from self.patients
            - failed if not provided is found from filtering out passed
                patients from eligible patients
        """

        if self.return_pt_querysets is False:
            return None

        if eligible is None or passed is None:
            raise ValueError("at least both of eligible and passed are required")

        if ineligible is None:
            ineligible = self.patients.exclude(
                # Subquery will execute on db level rather than python level
                pk__in=Subquery(eligible.values("pk"))
            )

        if failed is None:
            failed = eligible.exclude(
                # Subquery will execute on db level rather than python level
                pk__in=Subquery(passed.values("pk"))
            )

        return {
            "eligible": eligible,
            "ineligible": ineligible,
            "passed": passed,
            "failed": failed,
        }

    def calculate_kpi_1_total_eligible(self) -> KPIResult:
        """
        Calculates KPI 1: Total number of eligible patients
        Total number of patients with:
            * a valid NHS number
            * a valid date of birth
            * a valid PDU number
            * a visit date or admission date within the audit period
            * Below the age of 25 at the start of the audit period

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """

        # Set the query set as an attribute to be used in subsequent KPI calculations
        self.total_kpi_1_eligible_pts_base_query_set = self.patients.filter(
            # Valid attributes
            Q(nhs_number__isnull=False)
            & Q(date_of_birth__isnull=False)
            # Visit / admisison date within audit period
            & Q(visit__visit_date__range=(self.AUDIT_DATE_RANGE))
            # Below the age of 25 at the start of the audit period
            & Q(date_of_birth__gt=self.audit_start_date - relativedelta(years=25))
        ).distinct()  # When you filter on a related model field
        # (visit__visit_date__range), Django performs a join between the
        # Patient model and the Visit model. If a patient has multiple visits
        # that fall within the specified date range, the patient will appear
        # multiple times in the filtered queryset—once for each matching visit.

        # Count eligible patients and set as attribute
        # to be used in subsequent KPI calculations
        self.kpi_1_total_eligible = self.total_kpi_1_eligible_pts_base_query_set.count()
        total_eligible = self.kpi_1_total_eligible

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # Assuming total_passed is equal to total_number_of_eligible_patients_kpi_1 and total_failed is equal to total_ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=self.total_kpi_1_eligible_pts_base_query_set,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=self.total_kpi_1_eligible_pts_base_query_set,
            failed=self.total_kpi_1_eligible_pts_base_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_2_total_new_diagnoses(self) -> KPIResult:
        """
        Calculates KPI 2: Total number of new diagnoses within the audit period

        "Total number of patients with:
        * a valid NHS number
        *a valid date of birth
        *a valid PDU number
        * a visit date or admission date within the audit period
        * Below the age of 25 at the start of the audit period
        * Date of diagnosis within the audit period"

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """

        base_eligible_patients, _ = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        # This is same as KPI1 but with an additional filter for diagnosis date
        self.total_kpi_2_eligible_pts_base_query_set = base_eligible_patients.filter(
            Q(diagnosis_date__range=(self.AUDIT_DATE_RANGE))
        )

        # Count eligible patients
        self.kpi_2_total_eligible = self.total_kpi_2_eligible_pts_base_query_set.count()
        total_eligible = self.kpi_2_total_eligible

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=self.total_kpi_2_eligible_pts_base_query_set,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=self.total_kpi_1_eligible_pts_base_query_set,
            failed=self.total_kpi_1_eligible_pts_base_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_3_total_t1dm(self) -> KPIResult:
        """
        Calculates KPI 3: Total number of eligible patients with Type 1 diabetes
        Total number of patients with:
            * a valid NHS number
            *a valid date of birth
            *a valid PDU number
            * a visit date or admission date within the audit period
            * Below the age of 25 at the start of the audit period
            * Diagnosis of Type 1 diabetes"

        (1, Type 1 Insulin-Dependent Diabetes Mellitus)

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """
        base_eligible_patients, _ = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = base_eligible_patients.filter(
            # is type 1 diabetes
            Q(diabetes_type=DIABETES_TYPES[0][0])
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_4_total_t1dm_gte_12yo(self) -> KPIResult:
        """
        Calculates KPI 4: Number of patients aged 12+ with Type 1 diabetes
        Total number of patients with:
            * a valid NHS number
            *a valid date of birth
            *a valid PDU number
            * a visit date or admission date within the audit period
            * Below the age of 25 at the start of the audit period
            * Age 12 and above years at the start of the audit period
            * Diagnosis of Type 1 diabetes"

            NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to None
        """

        base_eligible_patients, _ = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = base_eligible_patients.filter(
            # Diagnosis of Type 1 diabetes
            Q(diabetes_type=DIABETES_TYPES[0][0])
            # Age 12 and above years at the start of the audit period
            & Q(date_of_birth__lte=self.audit_start_date - relativedelta(years=12))
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_5_total_t1dm_complete_year(self) -> KPIResult:
        """
        Calculates KPI 5: Total number of patients with T1DM who have completed a year of care
        "Total number of patients with:
        * a valid NHS number
        *a valid date of birth
        *a valid PDU number
        * a visit date or admission date within the audit period
        * Below the age of 25 at the start of the audit period* Diagnosis of Type 1 diabetes

        Excluding
        * Date of diagnosis within the audit period
        * Date of leaving service within the audit period
        * Date of death within the audit period"

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """
        # If we have not already calculated KPI 1, do so now to set
        total_kpi_1_eligible_pts_base_query_set, total_eligible_kpi_1 = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = total_kpi_1_eligible_pts_base_query_set.exclude(
            # EXCLUDE Date of diagnosis within the audit period
            Q(diagnosis_date__range=(self.AUDIT_DATE_RANGE))
            # EXCLUDE Date of leaving service within the audit period
            | (
                Q(
                    paediatric_diabetes_units__date_leaving_service__range=(
                        self.audit_start_date,
                        self.audit_end_date,
                    )
                )
            )
            # EXCLUDE Date of death within the audit period"
            | Q(death_date__range=(self.AUDIT_DATE_RANGE))
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()
        # We also use this as denominator for subsequent KPIS
        # so set as attributes
        self.total_kpi_5_eligible_pts_base_query_set = eligible_patients
        self.kpi_5_total_eligible = total_eligible

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_6_total_t1dm_complete_year_gte_12yo(self) -> KPIResult:
        """
        Calculates KPI 6: Total number of patients with T1DM who have completed a year of care and are aged 12 or older
        Total number of patients with:
        * a valid NHS number
        * an observation within the audit period
        * Age 12 and above at the start of the audit period
        * Diagnosis of Type 1 diabetes

        Excluding
        * Date of diagnosis within the audit period
        * Date of leaving service within the audit period
        * Date of death within the audit period

        NOTE: exclusion same as KPI5

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """

        # We cannot simply use KPI1 base queryset as that includes a filter
        # for age < 25. Additionally, this requires an observation within
        # the audit period, which is not included in KPI1 base queryset.
        # So need to make new query set

        # Separate exclusions from the main query for clarity
        eligible_patients_exclusions = self.patients.exclude(
            # EXCLUDE Date of diagnosis within the audit period
            Q(diagnosis_date__range=(self.AUDIT_DATE_RANGE))
            # EXCLUDE Date of leaving service within the audit period
            | (
                Q(
                    paediatric_diabetes_units__date_leaving_service__range=(
                        self.audit_start_date,
                        self.audit_end_date,
                    )
                )
            )
            # EXCLUDE Date of death within the audit period"
            | Q(death_date__range=(self.AUDIT_DATE_RANGE))
        )

        base_eligible_patients = eligible_patients_exclusions.filter(
            # Valid attributes
            Q(nhs_number__isnull=False)
            & Q(date_of_birth__isnull=False)
            # Age 12 and above at the start of the audit period
            & Q(date_of_birth__lte=self.audit_start_date - relativedelta(years=12))
            # Diagnosis of Type 1 diabetes
            & Q(diabetes_type=DIABETES_TYPES[0][0])
        )

        # Find patients with at least one observation within the audit period
        # this requires checking for a date in any of the Visits for a given
        # patient
        valid_visit_subquery = Visit.objects.filter(
            Q(
                Q(height_weight_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(hba1c_date__range=(self.AUDIT_DATE_RANGE))
                | Q(blood_pressure_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(foot_examination_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(retinal_screening_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(albumin_creatinine_ratio_date__range=(self.AUDIT_DATE_RANGE))
                | Q(total_cholesterol_date__range=(self.AUDIT_DATE_RANGE))
                | Q(thyroid_function_date__range=(self.AUDIT_DATE_RANGE))
                | Q(coeliac_screen_date__range=(self.AUDIT_DATE_RANGE))
                | Q(psychological_screening_assessment_date__range=(self.AUDIT_DATE_RANGE))
            ),
            patient=OuterRef("pk"),
            visit_date__range=self.AUDIT_DATE_RANGE,
        )

        # Check any observation across all visits
        eligible_pts_annotated_kpi_6_visits = base_eligible_patients.annotate(
            valid_kpi_6_visits=Exists(valid_visit_subquery)
        )

        eligible_patients = eligible_pts_annotated_kpi_6_visits.filter(valid_kpi_6_visits__gte=1)

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # We reuse this as a base query set for subsequent KPIs so set
        # as an attribute
        self.total_kpi_6_eligible_pts_base_query_set = eligible_patients
        self.kpi_6_total_eligible = total_eligible

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_7_total_new_diagnoses_t1dm(self) -> KPIResult:
        """
        Calculates KPI 7: Total number of new diagnoses of T1DM
        Total number of patients with:
        * a valid NHS number
        * an observation within the audit period
        * Age 0-24 years at the start of the audit period
        * Diagnosis of Type 1 diabetes
        * Date of diagnosis within the audit period

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """

        # total_kpi_1_eligible_pts_base_query_set is slightly different
        # (additionally specifies visit date). So we need to make a new
        # query set
        eligible_patients = self.patients.filter(
            # Valid attributes
            Q(nhs_number__isnull=False)
            & Q(date_of_birth__isnull=False)
            # * Age < 25y years at the start of the audit period
            & Q(date_of_birth__gt=self.audit_start_date - relativedelta(years=25))
            # Diagnosis of Type 1 diabetes
            & Q(diabetes_type=DIABETES_TYPES[0][0])
            & Q(diagnosis_date__range=self.AUDIT_DATE_RANGE)
            & (
                # an observation within the audit period
                # this requires checking for a date in any of the Visit model's
                # observation fields (found simply by searching for date fields
                # with the word 'observation' in the field verbose_name)
                Q(visit__height_weight_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__hba1c_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__blood_pressure_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__foot_examination_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__retinal_screening_observation_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__albumin_creatinine_ratio_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__total_cholesterol_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__thyroid_function_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__coeliac_screen_date__range=(self.AUDIT_DATE_RANGE))
                | Q(visit__psychological_screening_assessment_date__range=(self.AUDIT_DATE_RANGE))
            )
        ).distinct()  # the reason for distinct is same as KPI1 (see comments).
        # This time, was failing tests for KPI 41-42.

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # In case we need to use this as a base query set for subsequent KPIs
        self.total_kpi_7_eligible_pts_base_query_set = eligible_patients
        self.kpi_7_total_eligible = total_eligible

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_8_total_deaths(self) -> KPIResult:
        """
        Calculates KPI 8: Number of patients who died within audit period
        Number of eligible patients (measure 1) with:
            * a death date in the audit period

            NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """
        base_eligible_patients, _ = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = base_eligible_patients.filter(
            # Date of death within the audit period"
            Q(death_date__range=(self.AUDIT_DATE_RANGE))
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_9_total_service_transitions(self) -> KPIResult:
        """
        Calculates KPI 9: Number of patients who transitioned/left service within audit period

        Number of eligible patients (measure 1) with
        * a leaving date in the audit period

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """
        base_eligible_patients, _ = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = base_eligible_patients.filter(
            # a leaving date in the audit period
            Q(paediatric_diabetes_units__date_leaving_service__range=(self.AUDIT_DATE_RANGE))
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_10_total_coeliacs(self) -> KPIResult:
        """
        Calculates KPI 10: Total number of coeliacs
        Number of eligible patients (measure 1) who:

        * most recent observation for item 37 (based on visit date) is 1 = Yes
        // NOTE: item37 is _Has the patient been recommended a Gluten-free diet? _

        NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """
        # Define the subquery to find the latest visit where visit__gluten_free_diet = 1
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), gluten_free_diet=1)
            .order_by("-visit_date")
            .values("pk")[:1]
        )

        # Filter the Patient queryset based on the subquery
        base_query_set, _ = self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        eligible_patients = base_query_set.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_11_total_thyroids(self) -> KPIResult:
        """
        Calculates KPI 11: Number of patients with thyroid  disease
        Number of eligible patients (measure 1)
        who:
            * most recent observation for item 35 (based on visit date) is either 2 = Thyroxine for hypothyroidism or 3 = Antithyroid medication for hyperthyroidism
            // NOTE: item35 is _At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?_

            NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """
        # Define the subquery to find the latest visit where thyroid_treatment_status__in = 2 or 3
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), thyroid_treatment_status__in=[2, 3])
            .order_by("-visit_date")
            .values("pk")[:1]
        )

        # Filter the Patient queryset based on the subquery
        base_query_set, _ = self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        eligible_patients = base_query_set.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_12_total_ketone_test_equipment(self) -> KPIResult:
        """
        Calculates KPI 12: Number of patients using (or trained to use) blood ketone testing equipment

        Number of eligible patients (measure 1) whose
            * most recent observation for item 45 (based on visit date) is 1 = Yes
            // NOTE: item45 is _Was the patient using (or trained to use) blood ketone testing equipment at time of visit? _

            NOTE: just a count so pass/fail doesn't make sense; these should be
        discarded as they're set to the same value as eligible/ineligible in
        the returned KPIResult object.
        """
        # Define the subquery to find the latest visit where ketone_meter_training = 1
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), ketone_meter_training=1)
            .order_by("-visit_date")
            .values("pk")[:1]
        )

        # Filter the Patient queryset based on the subquery
        base_query_set, _ = self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        eligible_patients = base_query_set.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )

        # Count eligible patients
        total_eligible = eligible_patients.count()

        # Calculate ineligible patients
        total_ineligible = self.total_patients_count - total_eligible

        # This is just a count so pass/fail doesn't make sense; just set to same
        # as eligible/ineligible
        total_passed = None
        total_failed = None

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            # Just counts so pass/fail doesn't make sense; just set to same
            passed=eligible_patients,
            failed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_13_one_to_three_injections_per_day(
        self,
        eligible_patients: QuerySet[Patient],
    ) -> KPIResult:
        """
        Calculates KPI 13: One - three injections/day

        Numerator: Number of eligible patients whose most recent entry (based on visit date)
        for treatment regimen (item 20) is 1 = One-three injections/day

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
            if eligible_patients is None
            else (eligible_patients, eligible_patients.count())
        )

        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 1
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=1)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_14_four_or_more_injections_per_day(
        self,
        eligible_patients: QuerySet[Patient],
    ) -> KPIResult:
        """
        Calculates KPI 14: Four or more injections/day

        Numerator: Number of eligible patients whose most recent entry (based on visit date)
        for treatment regimen (item 20) is 2 = Four or more injections/day

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
            if eligible_patients is None
            else (eligible_patients, eligible_patients.count())
        )

        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 2
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=2)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_15_insulin_pump(
        self,
        eligible_patients: QuerySet[Patient],
    ) -> KPIResult:
        """
        Calculates KPI 15: Insulin pump (including those using a pump as part of a hybrid closed loop)

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for treatment
        regimen (item 20) is 3 = Insulin pump

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
            if eligible_patients is None
            else (eligible_patients, eligible_patients.count())
        )

        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 3
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=3)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_16_one_to_three_injections_plus_other_medication(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 16: One - three injections/day plus other blood glucose lowering medication

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for treatment regimen (item 20) is 4 = One - three injections/day plus other blood glucose lowering medication

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 4
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=4)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_17_four_or_more_injections_plus_other_medication(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 17: Four or more injections/day plus other blood glucose lowering medication

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for treatment regimen (item 20) is 5 = Four or more injections/day plus other blood glucose lowering medication

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 5
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=5)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_18_insulin_pump_plus_other_medication(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 18: Insulin pump therapy plus other blood glucose lowering medication

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for treatment regimen (item 20) is 6 = Insulin pump therapy plus other blood glucose lowering medication

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 6
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=6)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_19_dietary_management_alone(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 19: Dietary management alone (no insulin or other diabetes related medication)

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for treatment regimen (item 20) is 7 = Dietary management alone (no insulin or other diabetes related medication)

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 7
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=7)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_20_dietary_management_plus_other_medication(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 20: Dietary management plus other blood glucose lowering medication (non Type-1 diabetes)

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for treatment regimen (item 20) is 8 = Dietary management plus other blood glucose lowering medication (non Type-1 diabetes)

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where treatment_regimen = 8
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), treatment=8)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_21_flash_glucose_monitor(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 21: Number of patients using a flash glucose monitor

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for blood glucose monitoring (item 22) is either 2 = Flash glucose monitor or 3 = Modified flash glucose monitor (e.g. with MiaoMiao, Blucon etc.)

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where blood glucose monitoring (item 22) is either 2 = Flash glucose monitor or 3 = Modified flash glucose monitor (e.g. with MiaoMiao, Blucon etc.)
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), glucose_monitoring__in=[2, 3])
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_22_real_time_cgm_with_alarms(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 22: Number of patients using a real time continuous glucose monitor (CGM) with alarms

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for blood glucose monitoring (item 22) is 4 = Real time continuous glucose monitor with alarms

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where blood glucose monitoring (item 22) is 4 = Real time continuous glucose monitor with alarms
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), glucose_monitoring=4)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_23_type1_real_time_cgm_with_alarms(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 23: Number of patients with Type 1 diabetes using a real time continuous glucose monitor (CGM) with alarms

        Numerator: Total number of eligible patients with Type 1 diabetes (measure 2)

        Denominator: Number of eligible patients whose most recent entry (based on visit date) for blood glucose monitoring (item 22) is 4 = Real time continuous glucose monitor with alarms
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_2_eligible_pts_base_query_set_and_total_count()
        )

        total_ineligible = self.total_patients_count - total_eligible

        # Define the subquery to find the latest visit where blood glucose monitoring (item 22) is 4 = Real time continuous glucose monitor with alarms
        latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"), glucose_monitoring=4)
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        # Filter the Patient queryset based on the subquery
        passed_patients = eligible_patients.filter(
            Q(id__in=Subquery(Patient.objects.filter(visit__in=latest_visit_subquery).values("id")))
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_24_hybrid_closed_loop_system(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 24: Hybrid closed loop system (HCL)

        Denominator: Total number of eligible patients (measure 1)

        Numerator: Number of eligible patients whose most recent entry (based on visit date) for treatment regimen (item 20) is either
            * 3 = insulin pump
            * or 6 = Insulin pump therapy plus other blood glucose lowering medication

            AND whose most recent entry for item 21 (based on visit date) is either
            * 2 = Closed loop system (licenced)
            * or 3 = Closed loop system (DIY, unlicenced)
            * or 4 = Closed loop system (licence status unknown)
        """
        # Denominator
        total_kpi_1_eligible_pts_base_query_set, total_eligible_kpi_1 = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        # Eligible kpi24 patients are those who are either on an insulin pump or insulin pump therapy
        eligible_kpi_24_latest_visit_subquery = (
            Visit.objects.filter(patient=OuterRef("pk"))
            .filter(
                # Either:
                # 3 = insulin pump
                # or 6 = Insulin pump therapy plus other blood glucose lowering medication
                Q(treatment__in=[3, 6])
            )
            .order_by("-visit_date")
            .values("pk")[:1]
        )
        eligible_patients_kpi_24 = total_kpi_1_eligible_pts_base_query_set.filter(
            Q(
                id__in=Subquery(
                    Patient.objects.filter(visit__in=eligible_kpi_24_latest_visit_subquery).values(
                        "id"
                    )
                )
            )
        )
        total_eligible_kpi_24 = eligible_patients_kpi_24.count()

        # So ineligible patients are
        #   patients already ineligible for KPI 1
        #   PLUS
        #   the subset of total_kpi_1_eligible_pts_base_query_set
        #   who are ineligible for kpi24 (not on an insulin pump or insulin pump therapy)
        total_ineligible = (self.total_patients_count - total_eligible_kpi_1) + (
            total_eligible_kpi_1 - total_eligible_kpi_24
        )

        # Passing patients are the subset of kpi_24 eligible who are on closed loop system
        passing_patients = eligible_patients_kpi_24.filter(
            Q(
                id__in=Subquery(
                    Patient.objects.filter(
                        Q(visit__in=eligible_kpi_24_latest_visit_subquery)
                        # AND whose most recent entry for item 21 (based on visit date) is either
                        # * 2 = Closed loop system (licenced)
                        # * or 3 = Closed loop system (DIY, unlicenced)
                        # * or 4 = Closed loop system (licence status unknown)
                        & Q(visit__closed_loop_system__in=[2, 3, 4])
                    ).values("id")
                )
            )
        )
        total_passed = passing_patients.count()
        total_failed = eligible_patients_kpi_24.count() - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients_kpi_24,
            passed=passing_patients,
        )

        return KPIResult(
            total_eligible=total_eligible_kpi_24,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_25_hba1c(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 25: HbA1c (%)


        Numerator: Number of eligible patients with at least one valid entry for HbA1c value (item 17) with an observation date (item 19) within the audit period

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid entry for HbA1c value (item 17) with an observation date (item 19) within the audit period
        # This is simply patients with a visit with a valid HbA1c value
        passed_patients = eligible_patients.filter(
            Q(visit__hba1c__isnull=False),
            Q(visit__hba1c_date__range=(self.AUDIT_DATE_RANGE)),
        )
        total_passed = passed_patients.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=passed_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_26_bmi(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 26: BMI (%)

        Numerator: Number of eligible patients at least one valid entry for Patient Height (item 14) and for Patient Weight (item 15) with an observation date (item 16) within the audit period

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid entry for ht & wt within audit period
        total_passed_query_set = eligible_patients.filter(
            Q(visit__height__isnull=False),
            Q(visit__weight__isnull=False),
            # Within audit period
            Q(visit__height_weight_observation_date__range=(self.AUDIT_DATE_RANGE)),
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_27_thyroid_screen(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 27: Thyroid Screen (%)

        Numerator: Number of eligible patients with at least one entry for Thyroid function observation date (item 34) within the audit period

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid entry for thyroid screen within audit period
        total_passed_query_set = eligible_patients.filter(
            # Within audit period
            Q(visit__thyroid_function_date__range=(self.AUDIT_DATE_RANGE)),
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_28_blood_pressure(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 28: Blood Pressure (%)

        Numerator: Number of eligible patients with a valid entry for systolic measurement (item 23) with an observation date (item 25) within the audit period

        Denominator: Number of patients with Type 1 diabetes aged 12+ with a complete year of care in audit period (measure 6)

        # NOTE: Does not need a valid diastolic measurement
        """
        kpi_6_total_eligible_query_set, total_eligible_kpi_6 = (
            self._get_total_kpi_6_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_6_total_eligible_query_set
        total_eligible = total_eligible_kpi_6
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid entry for systolic measurement within audit period
        total_passed_query_set = eligible_patients.filter(
            # Within audit period
            Q(visit__systolic_blood_pressure__isnull=False),
            Q(visit__blood_pressure_observation_date__range=(self.AUDIT_DATE_RANGE)),
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_29_urinary_albumin(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 29: Urinary Albumin (%)

        Numerator: Number of eligible patients with at entry for Urinary Albumin Level (item 29) with an observation date (item 30) within the audit period

        Denominator: Number of patients with Type 1 diabetes aged 12+ with a complete year of care in audit period (measure 6)
        """
        kpi_6_total_eligible_query_set, total_eligible_kpi_6 = (
            self._get_total_kpi_6_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_6_total_eligible_query_set
        total_eligible = total_eligible_kpi_6
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid entry for Urinary Albumin Level (item 29)
        # with an observation date (item 30) within the audit period
        total_passed_query_set = eligible_patients.filter(
            Q(visit__albumin_creatinine_ratio__isnull=False),
            # Within audit period
            Q(visit__albumin_creatinine_ratio_date__range=(self.AUDIT_DATE_RANGE)),
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_30_retinal_screening(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 30: Retinal Screening (%)

        Numerator: Number of eligible patients with at least one entry for Retinal Screening Result (item 28) is either 1 = Normal or 2 = Abnormal AND the observation date (item 27) is within the audit period

        Denominator: Number of patients with Type 1 diabetes aged 12+ with a complete year of care in audit period (measure 6)
        """
        kpi_6_total_eligible_query_set, total_eligible_kpi_6 = (
            self._get_total_kpi_6_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_6_total_eligible_query_set
        total_eligible = total_eligible_kpi_6
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one for Retinal Screening Result (item 28) is either 1 = Normal or 2 = Abnormal AND the observation date (item 27) is within the audit period
        total_passed_query_set = eligible_patients.filter(
            Q(
                visit__retinal_screening_result__in=[
                    RETINAL_SCREENING_RESULTS[0][0],
                    RETINAL_SCREENING_RESULTS[1][0],
                ]
            ),
            # Within audit period
            Q(visit__retinal_screening_observation_date__range=(self.AUDIT_DATE_RANGE)),
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_31_foot_examination(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 31: Foot Examination (%)

        Numerator: Number of eligible patients with at least one entry for Foot Examination Date (item 26) within the audit period

        Denominator: Number of patients with Type 1 diabetes aged 12+ with a complete year of care in audit period (measure 6)
        """
        kpi_6_total_eligible_query_set, total_eligible_kpi_6 = (
            self._get_total_kpi_6_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_6_total_eligible_query_set
        total_eligible = total_eligible_kpi_6
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one for Foot Examination Date (item 26) within the audit period
        total_passed_query_set = eligible_patients.filter(
            # Within audit period
            Q(visit__foot_examination_observation_date__range=(self.AUDIT_DATE_RANGE)),
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    # TODO: get actual querysets for patients who passed and failed
    def calculate_kpi_32_1_health_check_completion_rate(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 32.1: Health check completion rate (%)
        Number of actual health checks over number of expected health checks.

        Numerator: health checks given
        - Patients = those with T1DM.
        - Patients < 12yo  => expected health checks = 3
            (HbA1c, BMI, Thyroid)
        - patients >= 12yo => expected health checks = 6
            (HbA1c, BMI, Thyroid, BP, Urinary Albumin, Foot Exam)

        Denominator: Number of expected health checks
            - 3 for CYP <12 years with T1D
            - 6 for CYP >= 12 years with T1D

        NOTE: KPIResult(
            total_eligible = total expected health checks,
            total_passed = total actual health checks,
            total_failed = total expected health checks - total actual health checks
            total_ineligible = ineligible PATIENTS
        )
        """

        # Get the eligible patients
        base_eligible_query_set, base_total_eligible = (
            # Pts with T1DM and a complete year of care
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - base_total_eligible

        # Separate the patients into those < 12yo and those >= 12yo
        eligible_patients_lt_12yo = self._get_eligible_pts_measure_5_lt_12yo()
        eligible_patients_gte_12yo = self._get_eligible_pts_measure_5_gte_12yo()

        # Count health checks for patients < 12yo
        # Involves looking at all their Visits, finding if at least 1 of each
        # of the 3 health checks was done (= 1), and then summing this
        hba1c_subquery_lt_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            hba1c__isnull=False,
            hba1c_date__range=self.AUDIT_DATE_RANGE,
        )
        bmi_subquery_lt_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            height__isnull=False,
            weight__isnull=False,
            height_weight_observation_date__range=self.AUDIT_DATE_RANGE,
        )
        thyroid_subquery_lt_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            thyroid_function_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate each check individually and convert True to 1, False to 0
        annotated_eligible_pts_lt_12yo = eligible_patients_lt_12yo.annotate(
            hba1c_check=Case(
                When(Exists(hba1c_subquery_lt_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            bmi_check=Case(
                When(Exists(bmi_subquery_lt_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            thyroid_check=Case(
                When(Exists(thyroid_subquery_lt_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )

        # Annotate each check count and sum them up
        actual_health_checks_lt_12yo = annotated_eligible_pts_lt_12yo.aggregate(
            total_hba1c_checks=Sum("hba1c_check"),
            total_bmi_checks=Sum("bmi_check"),
            total_thyroid_checks=Sum("thyroid_check"),
        )

        # Sum the counts to get the total health checks
        total_health_checks_lt_12yo = sum(
            actual_health_checks_lt_12yo.get(key) or 0
            for key in [
                "total_hba1c_checks",
                "total_bmi_checks",
                "total_thyroid_checks",
            ]
        )

        # Repeat the process for patients >= 12yo

        # Count health checks for patients >= 12yo
        # Involves looking at all their Visits, finding if at least 1 of each
        # of the 6 health checks was done (= 1), and then summing this
        hba1c_subquery_gte_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            hba1c__isnull=False,
            hba1c_date__range=self.AUDIT_DATE_RANGE,
        )
        bmi_subquery_gte_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            height__isnull=False,
            weight__isnull=False,
            height_weight_observation_date__range=self.AUDIT_DATE_RANGE,
        )
        thyroid_subquery_gte_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            thyroid_function_date__range=self.AUDIT_DATE_RANGE,
        )
        bp_subquery_gte_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            systolic_blood_pressure__isnull=False,
            blood_pressure_observation_date__range=self.AUDIT_DATE_RANGE,
        )
        urinary_albumin_subquery_gte_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            albumin_creatinine_ratio__isnull=False,
            albumin_creatinine_ratio_date__range=self.AUDIT_DATE_RANGE,
        )
        foot_exam_subquery_gte_12yo = Visit.objects.filter(
            patient=OuterRef("pk"),
            foot_examination_observation_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate each check individually and convert True to 1, False to 0
        annotated_eligible_pts_gte_12yo = eligible_patients_gte_12yo.annotate(
            hba1c_check=Case(
                When(Exists(hba1c_subquery_gte_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            bmi_check=Case(
                When(Exists(bmi_subquery_gte_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            thyroid_check=Case(
                When(Exists(thyroid_subquery_gte_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            bp_check=Case(
                When(Exists(bp_subquery_gte_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            urinary_albumin_check=Case(
                When(Exists(urinary_albumin_subquery_gte_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            foot_exam_check=Case(
                When(Exists(foot_exam_subquery_gte_12yo), then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )

        # Annotate each check count and sum them up
        actual_health_checks_gte_12yo = annotated_eligible_pts_gte_12yo.aggregate(
            total_hba1c_checks=Sum("hba1c_check"),
            total_bmi_checks=Sum("bmi_check"),
            total_thyroid_checks=Sum("thyroid_check"),
            total_bp_checks=Sum("bp_check"),
            total_urinary_albumin_checks=Sum("urinary_albumin_check"),
            total_foot_exam_checks=Sum("foot_exam_check"),
        )

        # Sum the counts to get the total health checks
        total_health_checks_gte_12yo = sum(
            actual_health_checks_gte_12yo.get(key) or 0
            for key in [
                "total_hba1c_checks",
                "total_bmi_checks",
                "total_thyroid_checks",
                "total_bp_checks",
                "total_urinary_albumin_checks",
                "total_foot_exam_checks",
            ]
        )

        actual_health_checks_overall = total_health_checks_lt_12yo + total_health_checks_gte_12yo

        expected_total_health_checks = (
            eligible_patients_lt_12yo.count() * 3 + eligible_patients_gte_12yo.count() * 6
        )

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=base_eligible_query_set,
            passed=eligible_patients_lt_12yo,
        )

        return KPIResult(
            total_eligible=expected_total_health_checks,
            total_ineligible=total_ineligible,
            total_passed=actual_health_checks_overall,
            total_failed=expected_total_health_checks - actual_health_checks_overall,
            patient_querysets=patient_querysets,
        )

    # TODO: get actual querysets for patients who passed and failed
    def calculate_kpi_32_2_health_check_lt_12yo(self) -> KPIResult:
        """
        Calculates KPI 32.2: Health Checks (Less than 12 years)

        Numerator: number of CYP with T1D under 12 years with all three health checks (HbA1c, BMI, Thyroid)

        Denominator:  number of CYP with T1D under 12 years
        """
        # Get the eligible patients
        eligible_patients = self._get_eligible_pts_measure_5_lt_12yo()
        total_eligible = eligible_patients.count()
        total_ineligible = self.total_patients_count - total_eligible

        # Count health checks for patients < 12yo
        # Involves looking at all their Visits, finding if at least 1 of each
        # of the 3 health checks was done (= 1), and then summing this if all
        # 3 checks are done
        hba1c_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            hba1c__isnull=False,
            hba1c_date__range=self.AUDIT_DATE_RANGE,
        )
        bmi_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            height__isnull=False,
            weight__isnull=False,
            height_weight_observation_date__range=self.AUDIT_DATE_RANGE,
        )
        thyroid_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            thyroid_function_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate each check individually and convert True to 1, False to 0
        annotated_eligible_pts = eligible_patients.annotate(
            hba1c_check=Case(
                When(Exists(hba1c_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            bmi_check=Case(
                When(Exists(bmi_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            thyroid_check=Case(
                When(Exists(thyroid_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            all_3_hcs_completed=Case(
                When(
                    Q(hba1c_check=1) & Q(bmi_check=1) & Q(thyroid_check=1),
                    then=1,
                ),
                default=0,
                output_field=IntegerField(),
            ),
        )

        total_passed = (
            annotated_eligible_pts.aggregate(
                total_pts_all_hcs_completed=Sum("all_3_hcs_completed")
            ).get("total_pts_all_hcs_completed")
            or 0
        )

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_eligible - total_passed,
            patient_querysets=patient_querysets,
        )

    # TODO: get actual querysets for patients who passed and failed
    def calculate_kpi_32_3_health_check_gte_12yo(self) -> KPIResult:
        """
        Calculates KPI 32.3: Health Checks (12 years and over)

        Numerator:  Number of CYP with T1D aged 12 years and over with all six
        health checks (HbA1c, BMI, Thyroid, BP, Urinary Albumin, Foot Exam)

        Denominator:  Number of CYP with T1D aged 12 years and over
        """
        # Get the eligible patients
        eligible_patients = self._get_eligible_pts_measure_5_gte_12yo()
        total_eligible = eligible_patients.count()
        total_ineligible = self.total_patients_count - total_eligible

        # Count health checks for patients >= 12yo
        # Involves looking at all their Visits, finding if at least 1 of each
        # of the 6 health checks was done (= 1), and then summing this if all
        # 6 checks are done
        hba1c_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            hba1c__isnull=False,
            hba1c_date__range=self.AUDIT_DATE_RANGE,
        )
        bmi_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            height__isnull=False,
            weight__isnull=False,
            height_weight_observation_date__range=self.AUDIT_DATE_RANGE,
        )
        thyroid_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            thyroid_function_date__range=self.AUDIT_DATE_RANGE,
        )
        bp_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            systolic_blood_pressure__isnull=False,
            blood_pressure_observation_date__range=self.AUDIT_DATE_RANGE,
        )
        urinary_albumin_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            albumin_creatinine_ratio__isnull=False,
            albumin_creatinine_ratio_date__range=self.AUDIT_DATE_RANGE,
        )
        foot_exam_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            foot_examination_observation_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate each check individually and convert True to 1, False to 0
        annotated_eligible_pts = eligible_patients.annotate(
            hba1c_check=Case(
                When(Exists(hba1c_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            bmi_check=Case(
                When(Exists(bmi_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            thyroid_check=Case(
                When(Exists(thyroid_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            bp_check=Case(
                When(Exists(bp_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            urinary_albumin_check=Case(
                When(Exists(urinary_albumin_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            foot_exam_check=Case(
                When(Exists(foot_exam_subquery), then=1),
                default=0,
                output_field=IntegerField(),
            ),
            all_6_hcs_completed=Case(
                When(
                    Q(hba1c_check=1)
                    & Q(bmi_check=1)
                    & Q(thyroid_check=1)
                    & Q(bp_check=1)
                    & Q(urinary_albumin_check=1)
                    & Q(foot_exam_check=1),
                    then=1,
                ),
                default=0,
                output_field=IntegerField(),
            ),
        )

        total_passed = (
            annotated_eligible_pts.aggregate(
                total_pts_all_hcs_completed=Sum("all_6_hcs_completed")
            ).get("total_pts_all_hcs_completed")
            or 0
        )

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_eligible - total_passed,
            patient_querysets=patient_querysets,
        )

    def _get_eligible_pts_measure_5_lt_12yo(self):
        """
        Returns the eligible patients for measure 5 who are under 12 years old
        """
        if hasattr(self, "eligible_pts_lt_12yo"):
            return self.eligible_pts_lt_12yo

        base_eligible_query_set, _ = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        self.eligible_patients_lt_12yo = base_eligible_query_set.filter(
            Q(date_of_birth__gt=self.audit_start_date - relativedelta(years=12))
        )

        return self.eligible_patients_lt_12yo

    def _get_eligible_pts_measure_5_gte_12yo(self):
        """
        Returns the eligible patients for measure 5 who are gte 12 years old
        """
        if hasattr(self, "eligible_patients_gte_12yo"):
            return self.eligible_patients_gte_12yo

        base_eligible_query_set, _ = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        self.eligible_patients_gte_12yo = base_eligible_query_set.filter(
            Q(date_of_birth__lte=self.audit_start_date - relativedelta(years=12))
        )

        return self.eligible_patients_gte_12yo

    def calculate_kpi_33_hba1c_4plus(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 33: HbA1c 4+ (%)

        Numerator: Number of eligible patients with at least four entries for HbA1c value (item 17) with an observation date (item 19) within the audit period

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least 4 entries for HbA1c value with associated
        # observation date within audit period

        # First get query set of patients with at least 4 valid HbA1c measures
        eligible_pts_annotated_hba1c_visits = eligible_patients.annotate(
            hba1c_valid_visits=Count(
                "visit",
                filter=Q(
                    visit__hba1c__isnull=False,
                    visit__hba1c_date__range=self.AUDIT_DATE_RANGE,
                ),
            )
        )
        total_passed_query_set = eligible_pts_annotated_hba1c_visits.filter(
            hba1c_valid_visits__gte=4
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_34_psychological_assessment(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 34: Psychological assessment (%)

        Numerator: Number of eligible patients with an entry for Psychological Screening Date (item 38) within the audit period

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with an entry for Psychological Screening Date
        # (item 38) within the audit period

        # First get query set of patients with at least 1 valid psych screen
        eligible_pts_annotated_psych_screen_visits = eligible_patients.annotate(
            psych_valid_visits=Count(
                "visit",
                filter=Q(
                    visit__psychological_screening_assessment_date__range=self.AUDIT_DATE_RANGE,
                ),
            )
        )
        total_passed_query_set = eligible_pts_annotated_psych_screen_visits.filter(
            psych_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_35_smoking_status_screened(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 35: Smoking status screened (%)

        Numerator: Number of eligible patients with at least one entry for Smoking Status (item 40) that is either 1 = Non-smoker or 2 = Curent smoker within the audit period (based on visit date)

        Denominator: Number of patients with Type 1 diabetes aged 12+ with a complete year of care in audit period (measure 6)
        """
        kpi_6_total_eligible_query_set, total_eligible_kpi_6 = (
            self._get_total_kpi_6_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_6_total_eligible_query_set
        total_eligible = total_eligible_kpi_6
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with a valid entry for Smoking status
        # Get the visits that match the valid smoking status criteria
        valid_smoking_visits = Visit.objects.filter(
            patient=OuterRef("pk"),
            visit_date__range=self.AUDIT_DATE_RANGE,
            smoking_status__in=[SMOKING_STATUS[0][0], SMOKING_STATUS[1][0]],
        )
        eligible_pts_annotated_smoke_screen_visits = eligible_patients.annotate(
            smoke_valid_visits=Exists(
                valid_smoking_visits
            )  # This ensures a boolean check if such visits exist
            # NOTE: spent far too long debugging why this would not work
            # by just using Count() and filter when the patient's first
            # Visit had no smoking status but the second did. Some underlying
            # join issue with the first None meaning no subsequent Visits
            # would be founted. Exists() implementation here solved this.
        )

        total_passed_query_set = eligible_pts_annotated_smoke_screen_visits.filter(
            smoke_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_36_referral_to_smoking_cessation_service(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 36: Referral to smoking cessation service (%)

        Numerator: Number of eligible patients with an entry for Date of Smoking Cessation Referral (item 41) within the audit period

        Denominator: Number of patients with Type 1 diabetes aged 12+ with a complete year of care in audit period (measure 6)
        """
        kpi_6_total_eligible_query_set, total_eligible_kpi_6 = (
            self._get_total_kpi_6_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_6_total_eligible_query_set
        total_eligible = total_eligible_kpi_6
        total_ineligible = self.total_patients_count - total_eligible

        # Get the visits that match the valid Smoking Cessation Referral date
        smoke_cessation_visits = Visit.objects.filter(
            patient=OuterRef("pk"),
            visit_date__range=self.AUDIT_DATE_RANGE,
            smoking_cessation_referral_date__range=self.AUDIT_DATE_RANGE,
        )
        # Find patients with a valid entry for Smoking Cessation Referral
        eligible_pts_annotated_smoke_screen_visits = eligible_patients.annotate(
            smoke_cessation_referral_valid_visits=Exists(smoke_cessation_visits)
        )

        total_passed_query_set = eligible_pts_annotated_smoke_screen_visits.filter(
            smoke_cessation_referral_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_37_additional_dietetic_appointment_offered(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 37: Additional dietetic appointment offered (%)

        Numerator: Numer of eligible patients with at least one entry for Additional Dietitian Appointment Offered (item 43) that is 1 = Yes within the audit period (based on visit date)

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one entry for Additional Dietitian Appointment Offered (item 43) that is 1 = Yes within the audit period (based on visit date)
        eligible_pts_annotated_dietician_offered_visits = eligible_patients.annotate(
            dietician_offered_valid_visits=Count(
                "visit",
                filter=Q(
                    visit__visit_date__range=self.AUDIT_DATE_RANGE,
                    visit__dietician_additional_appointment_offered=1,
                ),
            )
        )
        total_passed_query_set = eligible_pts_annotated_dietician_offered_visits.filter(
            dietician_offered_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_38_patients_attending_additional_dietetic_appointment(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 38: Patients attending additional dietetic appointment (%)

        Numerator: Number of eligible patients with at least one entry for Additional Dietitian Appointment Date (item 44) within the audit year

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one entry for Additional Dietitian
        # Appointment Date (item 44) within the audit year
        eligible_pts_annotated_dietician_additional_visits = eligible_patients.annotate(
            dietician_additional_valid_visits=Count(
                "visit",
                filter=Q(
                    visit__visit_date__range=self.AUDIT_DATE_RANGE,
                    visit__dietician_additional_appointment_date__range=self.AUDIT_DATE_RANGE,
                ),
            )
        )
        total_passed_query_set = eligible_pts_annotated_dietician_additional_visits.filter(
            dietician_additional_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_39_influenza_immunisation_recommended(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 39: Influenza immunisation recommended (%)

        Numerator: Number of eligible patients with at least one entry for Influzena Immunisation Recommended (item 24) within the audit period

        Denominator: Number of patients with Type 1 diabetes with a complete year of care in the audit period (measure 5)
        """
        kpi_5_total_eligible_query_set, total_eligible_kpi_5 = (
            self._get_total_kpi_5_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_5_total_eligible_query_set
        total_eligible = total_eligible_kpi_5
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one entry for Influzena Immunisation
        # Recommended (item 24) within the audit period
        eligible_pts_annotated_flu_immunisation_recommended_date_visits = (
            eligible_patients.annotate(
                flu_immunisation_recommended_date_valid_visits=Count(
                    "visit",
                    filter=Q(
                        visit__visit_date__range=self.AUDIT_DATE_RANGE,
                        visit__flu_immunisation_recommended_date__range=self.AUDIT_DATE_RANGE,
                    ),
                )
            )
        )
        total_passed_query_set = (
            eligible_pts_annotated_flu_immunisation_recommended_date_visits.filter(
                flu_immunisation_recommended_date_valid_visits__gte=1
            )
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_40_sick_day_rules_advice(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 40: Sick day rules advice (%)

        Numerator:Number of eligible patients with at least one entry for Sick
        Day Rules (item 47) within the audit period

        Denominator: Total number of eligible patients (measure 1)
        """
        kpi_1_total_eligible_query_set, total_eligible_kpi_1 = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )

        eligible_patients = kpi_1_total_eligible_query_set
        total_eligible = total_eligible_kpi_1
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one entry for Sick
        # Day Rules (item 47) within the audit period
        eligible_pts_annotated_sick_day_rules_visits = eligible_patients.annotate(
            sick_day_rules_valid_visits=Count(
                "visit",
                filter=Q(
                    visit__visit_date__range=self.AUDIT_DATE_RANGE,
                    visit__sick_day_rules_training_date__range=self.AUDIT_DATE_RANGE,
                ),
            )
        )
        total_passed_query_set = eligible_pts_annotated_sick_day_rules_visits.filter(
            sick_day_rules_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_41_coeliac_disease_screening(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 41: Coeliac diasease screening (%)

        Numerator: Number of eligible patients with an entry for Coeliac Disease Screening Date (item 36) within 90 days of Date of Diabetes Diagnosis (item 7)

        Denominator: Number of patients with Type 1 diabetes who were diagnosed at least 90 days before the end of the audit period.

        NOTE: denominator is essentially KPI7 (total new T1DM diagnoses) plus
        extra filter for diabetes diagnosis < (AUDIT_END_DATE - 90 DAYS)
        """
        eligible_patients, total_eligible = (
            self._get_total_pts_new_t1dm_diag_90D_before_audit_end_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with an entry for Coeliac Disease
        # Screening Date (item 36) 90 days before or after diabetes diagnosis
        # date
        eligible_pts_annotated_coeliac_screen_visits = eligible_patients.annotate(
            coeliac_screen_valid_visits=Count(
                "visit",
                # NOTE: relativedelta not supported
                filter=Q(
                    visit__coeliac_screen_date__gte=F("diagnosis_date") - timedelta(days=90),
                    visit__coeliac_screen_date__lte=F("diagnosis_date") + timedelta(days=90),
                ),
            )
        )
        total_passed_query_set = eligible_pts_annotated_coeliac_screen_visits.filter(
            coeliac_screen_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_42_thyroid_disease_screening(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 42: Thyroid disaese screening (%)

        Numerator: Number of eligible patients with an entry for Thyroid Function Observation Date (item 34) within 90 days (<= | >=) of Date of Diabetes Diagnosis (item 7)

        Denominator: Number of patients with Type 1 diabetes who were diagnosed at least 90 days before the end of the audit period

        (NOTE: measure 7 AND diabetes diagnosis date < (AUDIT_END_DATE - 90 days))
        """
        eligible_patients, total_eligible = (
            self._get_total_pts_new_t1dm_diag_90D_before_audit_end_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with an entry for Thyroid Function Observation Date
        # (item 36) 90 days before or after diabetes diagnosis date
        eligible_pts_annotated_thyroid_fn_date_visits = eligible_patients.annotate(
            thyroid_fn_date_valid_visits=Count(
                "visit",
                # NOTE: relativedelta not supported
                filter=Q(
                    visit__thyroid_function_date__gte=F("diagnosis_date") - timedelta(days=90),
                    visit__thyroid_function_date__lte=F("diagnosis_date") + timedelta(days=90),
                ),
            )
        )
        total_passed_query_set = eligible_pts_annotated_thyroid_fn_date_visits.filter(
            thyroid_fn_date_valid_visits__gte=1
        )

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_43_carbohydrate_counting_education(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 43: Carbohydrate counting education (%)

        Numerator: Number of eligible patients with an entry for Carbohydrate
        Counting Education (item 42) within 7 days before or 14 days after the
        Date of Diabetes Diagnosis (item 7)

        Denominator: Number of patients with Type 1 diabetes who were diagnosed
        at least 14 days before the end of the audit period (<= | >=)

        (NOTE: Measure 7 AND diabetes diagnosis date < (AUDIT_END_DATE - 14 days))
        """

        # Eligible patients are measure 7 with
        # diagnosis date < (AUDIT_END_DATE - 14 days)
        base_eligible_patients, _ = (
            self._get_total_kpi_7_eligible_pts_base_query_set_and_total_count()
        )
        eligible_patients = base_eligible_patients.filter(
            diagnosis_date__lt=self.audit_end_date - relativedelta(days=14)
        )
        total_eligible = eligible_patients.count()
        total_ineligible = self.total_patients_count - total_eligible

        # Find visits with an entry for Carbohydrate Counting Education
        # (item 42) within 7 days before or 14 days after the
        # Date of Diabetes Diagnosis (item 7)
        valid_visit_subquery = Visit.objects.filter(
            patient=OuterRef("pk"),
            carbohydrate_counting_level_three_education_date__gte=F("patient__diagnosis_date")
            - timedelta(days=7),
            carbohydrate_counting_level_three_education_date__lte=F("patient__diagnosis_date")
            + timedelta(days=14),
        )

        # Annotate eligible patients with a boolean indicating the existence
        # of a valid Visit. NOTE: doing this because Count has weird behavior
        # if the first Visit has no valid carb date even if second does
        eligible_pts_annotated = eligible_patients.annotate(
            has_valid_visit=Exists(valid_visit_subquery)
        )

        # Filter patients who have at least one valid Visit
        total_passed_query_set = eligible_pts_annotated.filter(has_valid_visit=True)

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_44_mean_hba1c(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 44: Mean HbA1c

        SINGLE NUMBER: Mean of HbA1c measurements (item 17) within the audit
        period, excluding measurements taken within 90 days of diagnosis
        NOTE: The median for each patient is calculated. We then calculate the
        mean of the medians.

        Denominator: Total number of eligible patients (measure 1)

        NOTE: for pt querysets, only `eligible` and `ineligible` are valid, the
            others should be discarded.
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Calculate median HBa1c for each patient
        visit_value_cols = ["patient__pk", "hba1c"]
        # Retrieve all visits with valid HbA1c values
        valid_visits = Visit.objects.filter(
            visit_date__range=self.AUDIT_DATE_RANGE,
            hba1c_date__gt=F("patient__diagnosis_date") + timedelta(days=90),
            patient__in=eligible_patients,
        ).values(*visit_value_cols)

        # Group HbA1c values by patient ID into a list so can use
        # calculate_median method
        # We're doing this in Python instead of Django ORM because median
        # aggregation gets complicated
        hba1c_values_by_patient = defaultdict(list)
        for visit in valid_visits:
            hba1c_values_by_patient[visit["patient__pk"]].append(visit["hba1c"])

        # For each patient, calculate the median of their HbA1c values
        median_hba1cs = []
        for _, hba1c_values in hba1c_values_by_patient.items():
            median_hba1cs.append(self.calculate_median(hba1c_values))

        # Finally calculate the mean of the medians
        mean_of_median_hba1cs = self.calculate_mean(median_hba1cs)

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            # Use passed for storing the value
            total_passed=mean_of_median_hba1cs,
            # Failed is not used
            total_failed=-1,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_45_median_hba1c(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 43: Median HbA1c

        SINGLE NUMBER: median of HbA1c measurements (item 17) within the audit
        period, excluding measurements taken within 90 days of diagnosis

        i.e. valid = hba1c date > diagnosis date + 90 days

        NOTE: The median for each patient is calculated. We then calculate the
        median of the medians.

        Denominator: Total number of eligible patients (measure 1)

        NOTE: for pt querysets, only `eligible` and `ineligible` are valid, the
            others should be discarded.
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Calculate median HBa1c for each patient

        # Retrieve all visits with valid HbA1c values
        valid_visits = self._get_valid_visits_for_kpi_44_and_45(
            eligible_patients=eligible_patients,
        ).values("patient__pk", "hba1c")

        # Group HbA1c values by patient ID into a list so can use
        # calculate_median method
        # We're doing this in Python instead of Django ORM because median
        # aggregation gets complicated
        hba1c_values_by_patient = defaultdict(list)
        for visit in valid_visits:
            hba1c_values_by_patient[visit["patient__pk"]].append(visit["hba1c"])

        # For each patient, calculate the median of their HbA1c values
        median_hba1cs = []
        for _, hba1c_values in hba1c_values_by_patient.items():
            median_hba1cs.append(self.calculate_median(hba1c_values))

        # Finally calculate the median of the medians
        median_of_median_hba1cs = self.calculate_median(median_hba1cs)

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=eligible_patients,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            # Use passed for storing the value
            total_passed=median_of_median_hba1cs,
            # Failed is not used
            total_failed=-1,
            patient_querysets=patient_querysets,
        )

    def _get_valid_visits_for_kpi_44_and_45(
        self,
        eligible_patients: QuerySet[Patient],
    ) -> QuerySet[Visit]:
        """Enable query re-use as dashboard requires stratification by diabetes type
        but these calculations do not"""
        return Visit.objects.filter(
            visit_date__range=self.AUDIT_DATE_RANGE,
            hba1c_date__gt=F("patient__diagnosis_date") + timedelta(days=90),
            patient__in=eligible_patients,
        )

    def calculate_kpi_hba1c_vals_stratified_by_diabetes_type(self):
        """
        Calculates KPI 44 and 45 stratified by diabetes type for dashboard.

        Can't re-use the existing methods as they don't stratify.
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Filter eligible patients to just relevant diabetes types
        eligible_patients_t1dm = eligible_patients.filter(diabetes_type=DIABETES_TYPES[0][0])
        eligible_patients_t2dm = eligible_patients.filter(diabetes_type=DIABETES_TYPES[1][0])

        hba1c_vals = {
            "t1dm": {},
            "t2dm": {},
        }
        for key, eligible_pts in zip(
            ("t1dm", "t2dm"),
            (eligible_patients_t1dm, eligible_patients_t2dm),
        ):

            # Retrieve all visits with valid HbA1c values
            valid_visits = self._get_valid_visits_for_kpi_44_and_45(
                eligible_patients=eligible_pts,
            ).values("patient__pk", "hba1c")

            hba1c_vals[key]["mean"] = round(self._calculate_mean_hba1cs(valid_visits), 1)
            hba1c_vals[key]["median"] = round(self._calculate_median_hba1cs(valid_visits), 1)

        return hba1c_vals

    def _calculate_mean_hba1cs(
        self,
        valid_visits: QuerySet[Visit],
    ):
        # Group HbA1c values by patient ID into a list so can use
        # calculate_median method
        # We're doing this in Python instead of Django ORM because median
        # aggregation gets complicated
        hba1c_values_by_patient = defaultdict(list)
        for visit in valid_visits:
            hba1c_values_by_patient[visit["patient__pk"]].append(visit["hba1c"])

        # For each patient, calculate the median of their HbA1c values
        median_hba1cs = []
        for _, hba1c_values in hba1c_values_by_patient.items():
            median_hba1cs.append(self.calculate_median(hba1c_values))

        # Finally calculate the mean of the medians
        mean_of_median_hba1cs = self.calculate_mean(median_hba1cs)
        return mean_of_median_hba1cs

    def _calculate_median_hba1cs(
        self,
        valid_visits: QuerySet[Visit],
    ):
        # Group HbA1c values by patient ID into a list so can use
        # calculate_median method
        # We're doing this in Python instead of Django ORM because median
        # aggregation gets complicated
        hba1c_values_by_patient = defaultdict(list)
        for visit in valid_visits:
            hba1c_values_by_patient[visit["patient__pk"]].append(visit["hba1c"])

        # For each patient, calculate the median of their HbA1c values
        median_hba1cs = []
        for _, hba1c_values in hba1c_values_by_patient.items():
            median_hba1cs.append(self.calculate_median(hba1c_values))

        # Finally calculate the median of the medians
        median_of_median_hba1cs = self.calculate_median(median_hba1cs)
        return median_of_median_hba1cs

    def calculate_kpi_46_number_of_admissions(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 46: Number of admissions

        Numerator:Total number of admissions with a valid reason for admission
        (item 50) AND with a start date (item 48) OR discharge date (item 49)
        within the audit period
        NOTE: There can be more than one admission per patient, but eliminate
        duplicate entries


        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid admission
        # Get the visits that match the valid admission criteria
        valid_visit_subquery = Visit.objects.filter(
            # admission start date OR discharge date within audit period
            Q(
                Q(hospital_admission_date__range=self.AUDIT_DATE_RANGE)
                | Q(hospital_discharge_date__range=self.AUDIT_DATE_RANGE)
            ),
            # valid reason for admission
            hospital_admission_reason__in=[choice[0] for choice in HOSPITAL_ADMISSION_REASONS],
            patient=OuterRef("pk"),
            visit_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate eligible patients with a boolean indicating the existence
        # of a valid Visit. NOTE: doing this because Count has weird behavior
        # if the first Visit has no valid value even if second does
        eligible_pts_annotated = eligible_patients.annotate(
            has_valid_visit=Exists(valid_visit_subquery)
        )

        # Filter patients who have at least one valid Visit
        total_passed_query_set = eligible_pts_annotated.filter(has_valid_visit=True)

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_47_number_of_dka_admissions(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 47: Number of DKA admissions


        Numerator:Total number of admissions with a reason for admission
        (item 50) that is 2 = DKA AND with a start date (item 48) OR
        discharge date (item 49) within the audit period
        NOTE: There can be more than one admission per patient, but eliminate
        duplicate entries

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid DKA admission criteria
        # Get the visits that match the valid DKA admission criteria
        valid_visit_subquery = Visit.objects.filter(
            # admission start date OR discharge date within audit period
            Q(
                Q(hospital_admission_date__range=self.AUDIT_DATE_RANGE)
                | Q(hospital_discharge_date__range=self.AUDIT_DATE_RANGE)
            ),
            # DKA reason 2
            hospital_admission_reason=HOSPITAL_ADMISSION_REASONS[1][0],
            patient=OuterRef("pk"),
            visit_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate eligible patients with a boolean indicating the existence
        # of a valid Visit. NOTE: doing this because Count has weird behavior
        # if the first Visit has no valid value even if second does
        eligible_pts_annotated = eligible_patients.annotate(
            has_valid_visit=Exists(valid_visit_subquery)
        )

        # Filter patients who have at least one valid Visit
        total_passed_query_set = eligible_pts_annotated.filter(has_valid_visit=True)

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_48_required_additional_psychological_support(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 48: Required additional psychological support

        Numerator:Total number of eligible patients with at least one entry for
        Psychological Support (item 39) that is 1 = Yes within the audit period
        (based on visit date)

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid psych support criteria
        # Get the visits that match the valid psych support=1 criteria
        valid_visit_subquery = Visit.objects.filter(
            # required additional psychological support
            psychological_additional_support_status=YES_NO_UNKNOWN[0][0],
            patient=OuterRef("pk"),
            visit_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate eligible patients with a boolean indicating the existence
        # of a valid Visit. NOTE: doing this because Count has weird behavior
        # if the first Visit has no valid value even if second does
        eligible_pts_annotated = eligible_patients.annotate(
            has_valid_visit=Exists(valid_visit_subquery)
        )

        # Filter patients who have at least one valid Visit
        total_passed_query_set = eligible_pts_annotated.filter(has_valid_visit=True)

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def calculate_kpi_49_albuminuria_present(
        self,
    ) -> KPIResult:
        """
        Calculates KPI 49: Albuminuria present

        Numerator: Total number of eligible patients whose most recent
        entry for for Albuminuria Stage (item 31) based on observation date
        (item 30) is 2 = Microalbuminuria or 3 = Macroalbuminuria

        Denominator: Total number of eligible patients (measure 1)
        """
        eligible_patients, total_eligible = (
            self._get_total_kpi_1_eligible_pts_base_query_set_and_total_count()
        )
        total_ineligible = self.total_patients_count - total_eligible

        # Find patients with at least one valid albuminuria stage criteria
        # Get the visits that match the valid albuminuria criteria
        valid_visit_subquery = Visit.objects.filter(
            # valid albuminuria stage 2 or 3
            albuminuria_stage__in=[
                ALBUMINURIA_STAGES[1][0],
                ALBUMINURIA_STAGES[2][0],
            ],
            patient=OuterRef("pk"),
            visit_date__range=self.AUDIT_DATE_RANGE,
        )

        # Annotate eligible patients with a boolean indicating the existence
        # of a valid Visit. NOTE: doing this because Count has weird behavior
        # if the first Visit has no valid value even if second does
        eligible_pts_annotated = eligible_patients.annotate(
            has_valid_visit=Exists(valid_visit_subquery)
        )

        # Filter patients who have at least one valid Visit
        total_passed_query_set = eligible_pts_annotated.filter(has_valid_visit=True)

        total_passed = total_passed_query_set.count()
        total_failed = total_eligible - total_passed

        # Also set pt querysets to be returned if required
        patient_querysets = self._get_pt_querysets_object(
            eligible=eligible_patients,
            passed=total_passed_query_set,
        )

        return KPIResult(
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            total_passed=total_passed,
            total_failed=total_failed,
            patient_querysets=patient_querysets,
        )

    def _debug_helper_print_postcode_and_attrs(self, patient_queryset, *attrs):
        """Helper function to be used with tests which prints out the postcode
        and specified attributes for each patient in the queryset
        """

        logger.debug(f"===QuerySet:{str(patient_queryset)}===")
        logger.debug(f"==={self.AUDIT_DATE_RANGE=}===\n")
        for item in patient_queryset.values("postcode", *attrs):
            logger.debug(f'Patient Name: {item["postcode"]}')
            del item["postcode"]
            logger.debug(pformat(item) + "\n")

        logger.debug(f"====================")

    def _get_total_kpi_1_eligible_pts_base_query_set_and_total_count(
        self,
    ) -> Tuple[QuerySet[Patient], int]:
        """Enables reuse of the base query set for KPI 1

        If running calculation methods in order, this attribute will be set in calculate_kpi_1_total_eligible().

        If running another kpi calculation standalone, need to run that method first to have the attribute set.

        Returns:
            QuerySet: Base query set of eligible patients for KPI 1
            int: base query set count of total eligible patients for KPI 1
        """

        if not hasattr(self, "total_kpi_1_eligible_pts_base_query_set"):
            self.calculate_kpi_1_total_eligible()

        return (
            self.total_kpi_1_eligible_pts_base_query_set,
            self.kpi_1_total_eligible,
        )

    def _get_total_kpi_2_eligible_pts_base_query_set_and_total_count(
        self,
    ) -> Tuple[QuerySet[Patient], int]:
        """Enables reuse of the base query set for KPI 2

        If running calculation methods in order, this attribute will be set in calculate_kpi_2_total_new_diagnoses().

        If running another kpi calculation standalone, need to run that method first to have the attribute set.

        Returns:
            QuerySet: Base query set of eligible patients for KPI 2
            int: base query set count of total eligible patients for KPI 2
        """

        if not hasattr(self, "total_kpi_2_eligible_pts_base_query_set"):
            self.calculate_kpi_2_total_new_diagnoses()

        return (
            self.total_kpi_2_eligible_pts_base_query_set,
            self.kpi_2_total_eligible,
        )

    def _get_total_kpi_5_eligible_pts_base_query_set_and_total_count(
        self,
    ) -> Tuple[QuerySet, int]:
        """Enables reuse of the base query set for KPI 5

        If running calculation methods in order, this attribute will be set in calculate_kpi_5_total_t1dm_complete_year().

        If running another kpi calculation standalone, need to run that method first to have the attribute set.

        Returns:
            QuerySet: Base query set of eligible patients for KPI 5
            int: base query set count of total eligible patients for KPI 5
        """

        if not hasattr(self, "total_kpi_1_eligible_pts_base_query_set"):
            self.calculate_kpi_5_total_t1dm_complete_year()

        return (
            self.total_kpi_5_eligible_pts_base_query_set,
            self.kpi_5_total_eligible,
        )

    def _get_total_kpi_6_eligible_pts_base_query_set_and_total_count(
        self,
    ) -> Tuple[QuerySet, int]:
        """Enables reuse of the base query set for KPI 6

        If running calculation methods in order, this attribute will be set in calculate_kpi_6_total_t1dm_complete_year_gte_12yo().

        If running another kpi calculation standalone, need to run that method first to have the attribute set.

        Returns:
            QuerySet: Base query set of eligible patients for KPI 6
            int: base query set count of total eligible patients for KPI 6
        """

        if not hasattr(self, "total_kpi_1_eligible_pts_base_query_set"):
            self.calculate_kpi_6_total_t1dm_complete_year_gte_12yo()

        return (
            self.total_kpi_6_eligible_pts_base_query_set,
            self.kpi_6_total_eligible,
        )

    def _get_total_kpi_7_eligible_pts_base_query_set_and_total_count(
        self,
    ) -> Tuple[QuerySet, int]:
        """Enables reuse of the base query set for KPI 7

        If running calculation methods in order, this attribute will be set in calculate_kpi_7_total_t1dm_complete_year_gte_12yo().

        If running another kpi calculation standalone, need to run that method first to have the attribute set.

        Returns:
            QuerySet: Base query set of eligible patients for KPI 7
            int: base query set count of total eligible patients for KPI 7
        """

        if not hasattr(self, "total_kpi_1_eligible_pts_base_query_set"):
            self.calculate_kpi_7_total_new_diagnoses_t1dm()

        return (
            self.total_kpi_7_eligible_pts_base_query_set,
            self.kpi_7_total_eligible,
        )

    def _get_total_pts_new_t1dm_diag_90D_before_audit_end_base_query_set_and_total_count(
        self,
    ) -> Tuple[QuerySet, int]:
        """Enables reuse of the base query set for denominator in KPIS 41-43
        (patients with new T1DM, diagnosed at least 90 days before audit end
        date).

        Returns:
            QuerySet: Base query set of eligible patients for KPIs 41-43
            int: base query set count of total eligible patients for KPI 41-43

        NOTE: this is essentially KPI 7 plus an extra filter for diagnosis_date
        < 90 days before audit end date
        """

        # This might be run already so check if attribute exists
        if hasattr(self, "t1dm_pts_diagnosed_90D_before_end_base_query_set"):
            return (
                self.t1dm_pts_diagnosed_90D_before_end_base_query_set,
                self.t1dm_pts_diagnosed_90D_before_end_total_eligible,
            )

        # First get new T1DM diagnoses pts
        base_query_set, _ = self._get_total_kpi_7_eligible_pts_base_query_set_and_total_count()

        # Filter for those diagnoses at least 90 days before audit end date
        self.t1dm_pts_diagnosed_90D_before_end_base_query_set = base_query_set.filter(
            diagnosis_date__lt=self.audit_end_date - relativedelta(days=90),
        )
        self.t1dm_pts_diagnosed_90D_before_end_total_eligible = (
            self.t1dm_pts_diagnosed_90D_before_end_base_query_set.count()
        )

        return (
            self.t1dm_pts_diagnosed_90D_before_end_base_query_set,
            self.t1dm_pts_diagnosed_90D_before_end_total_eligible,
        )

    def calculate_median(self, values: list[Decimal]) -> float:
        """Calculates the median of a list of values

        Args:
            values (list[Decimal]): List of values to calculate the median for.
            assuming used with hba1c values which come in as Decimals. Convert
            these to floats for convenience.

        Returns:
            float: Median of the list of values. Returns -1 if no values
        """
        if not values:
            return float(-1)

        # Remove the None values and ensure they're sorted
        cleaned_values = [val for val in values if val is not None]
        if len(cleaned_values) == 0:
            return float(-1)

        cleaned_values.sort()

        length = len(values)
        if length % 2 == 0:

            # even number, take mean
            middle_1 = cleaned_values[(length // 2) - 1]
            middle_2 = cleaned_values[length // 2]
            return float((middle_1 + middle_2) / 2)

        # odd number
        middle = cleaned_values[length // 2]
        return float(middle)

    def calculate_mean(self, values: list[Decimal]) -> float:
        """Calculates the mean of a list of values

        Args:
            values (list[Decimal]): List of values to calculate the mean for.
            assuming used with hba1c values which come in as Decimals. Convert
            these to floats for convenience.

        Returns:
            float: Mean of the list of values. Returns -1 if no values
        """
        if not values:
            return float(-1)

        # Remove the None values
        cleaned_values = [val for val in values if val is not None]
        if len(cleaned_values) == 0:
            return float(-1)

        return float(sum(cleaned_values) / len(cleaned_values))
