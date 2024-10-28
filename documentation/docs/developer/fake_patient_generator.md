# `FakePatientCreator`

The `FakePatientCreator` is a utility class designed to generate realistic test data for patient objects and their corresponding visits. This guide will demonstrate how to use it within Django tests to create patients and associated visit data while ensuring specific attributes are valid, such as the date ranges and age categories.

## Overview

`FakePatientCreator` uses:

- A defined **audit period** for setting important date fields such as patient **date of birth**, **diagnosis date**, and **visit dates**.
- Random generation of visit types and allocation of patients to ensure realistic test scenarios.

The following steps provide an example test that ensures patients' ages fall within the expected range and visits are generated accordingly.

## Usage

### Initialise with Audit Period

We initialise the FakePatientCreator with a specific audit period as
this is used throughout the creation of fake patients and visits
including:

- setting random date of birth so max age by audit_start_date is valid
    for the given AgeRange. Also, diagnosis_date is between
    date_of_birth and audit_start_date.

- setting random diagnosis date so it is before audit_start_date

- Visit dates are spread evenly throughout each quarter of the audit
    period. For each Visit, the date is randomly set within its
    quarter's date range.

```python
from project.npda.general_functions.data_generator_extended import (
    FakePatientCreator,
    HbA1cTargetRange,
    VisitType,
)

# Set necessary attributes to calibrate all dates
DATE_IN_AUDIT = date(2024, 4, 1)
audit_start_date, audit_end_date = get_audit_period_for_date(DATE_IN_AUDIT)

fake_patient_creator = FakePatientCreator(
    audit_start_date=audit_start_date,
    audit_end_date=audit_end_date,
)
```

The `FakePatientCreator` provides utility methods to generate and save test data for patients and their corresponding visits. This guide describes the usage of the following three key methods:

1. `build_fake_patients`: Builds fake patient objects.
2. `build_fake_visits`: Builds fake visit objects for patients.
3. `create_and_save_fake_patients`: Combines patient and visit creation and saves them to the database.

### `build_fake_patients`

The `build_fake_patients` method generates a list of `n` fake patient objects but does **not** save them to the database. This is useful when you want to create patients but manipulate them further before committing them to the database.

#### Method Signature

```python
def build_fake_patients(
    self,
    n: int,
    age_range: AgeRange,
    **patient_kwargs,
) -> list[Patient]:
```

**Parameters**:

- n (int): The number of patients to create.
- age_range (AgeRange): The age range to assign to the patients (e.g., AgeRange.AGE_0_4).
- \*\*patient_kwargs (optional): Additional keyword arguments to pass to the PatientFactory, which allows customising fields like postcode.

**Example Usage:**

```python
# Create 10 fake patients within the age range 0-4
patients = fake_patient_creator.build_fake_patients(
    n=10,
    age_range=AgeRange.AGE_0_4,
    postcode="fake_postcode",  # Customise as needed
)
```

**Returns:**

- A list of Patient objects that are not yet saved to the database.

### `build_fake_visits`

The `build_fake_visits` method generates fake Visit objects for each patient and distributes these visits across different quarters of the audit period.

#### Method Signature

```python
def build_fake_visits(
    self,
    patients: list[Patient],
    age_range: AgeRange,
    hb1ac_target_range: HbA1cTargetRange = HbA1cTargetRange.TARGET,
    visit_types: list[VisitType] = DEFAULT_VISIT_TYPE,
    **visit_kwargs,
) -> list[Visit]:
```

**Parameters:**

- patients (list[Patient]): The list of patients for whom the visits are being created.
- age_range (AgeRange): The age range of the patients to guide the visit characteristics.
- hb1ac_target_range (HbA1cTargetRange, optional): The HbA1c target range for the visits, defaults to TARGET.
- visit_types (list[VisitType], optional): A list of visit types to be assigned to each patient, e.g., VisitType.CLINIC, VisitType.ANNUAL_REVIEW.
- \*\*visit_kwargs (optional): Additional keyword arguments for customising the visit creation, such as is_valid=True.

**Method Behavior:**

- Visits are distributed evenly across the quarters of the audit period. For example, if 12 visits are assigned, 3 will occur in each quarter.
- For each quarter, visit dates are randomly assigned within the quarter's date range.

#### Example Usage:

```python
# Generate 12 random visit types
VISIT_TYPES = generate_random_visit_types(n=12)

# Build visits for patients
visits = fake_patient_creator.build_fake_visits(
    patients=patients,
    age_range=AgeRange.AGE_0_4,
    hb1ac_target_range=HbA1cTargetRange.WELL_ABOVE,
    visit_types=VISIT_TYPES,
    is_valid=True  # Customise additional fields if necessary
)
```

Returns a list of Visit objects corresponding to the patients.

### `create_and_save_fake_patients`

The `create_and_save_fake_patients` method handles both patient and visit creation in a single process and saves them to the database. It bulk creates the patients and their associated visits to improve performance.

#### Method Signature

```python
def create_and_save_fake_patients(
    self,
    n: int,
    age_range: AgeRange,
    hb1ac_target_range: HbA1cTargetRange = HbA1cTargetRange.TARGET,
    visit_types: list[VisitType] = DEFAULT_VISIT_TYPE,
    **patient_kwargs,
) -> list[Patient]:
```

**Parameters:**

- n (int): The number of patients to create and save.
- age_range (AgeRange): The age range of the patients.
- hb1ac_target_range (HbA1cTargetRange, optional): The HbA1c target range, defaulting to TARGET.
- visit_types (list[VisitType], optional): A list of visit types to be created for each patient.
- \*\*patient_kwargs (optional): Additional keyword arguments for patient creation, such as postcode="123".

#### Example Usage

```python
# Create and save 100 patients with associated visits
saved_patients = fake_patient_creator.create_and_save_fake_patients(
    n=100,
    age_range=AgeRange.AGE_25_34,
    visit_types=[VisitType.CLINIC, VisitType.ANNUAL_REVIEW],
    postcode="fake_postcode"  # Customise as needed
)
```

Returns a list of Patient objects that have been saved to the database, each with their associated visits.

### Full Example

Below is an example test that demonstrates usage.

```python
import pytest
from datetime import date
from app.models import AgeRange, VisitType, HbA1cTargetRange
from app.utils import FakePatientCreator, get_audit_period_for_date

@pytest.mark.django_db
def test_example_use_fake_patient_creator():
    """Tests that the ages of all fake patients fall into the appropriate
    age range.

    NOTE:
    We initialise the FakePatientCreator with a specific audit period as
    this is used throughout the creation of fake patients and visits
    including:
        - setting random date of birth so max age by audit_start_date is valid
            for the given AgeRange. Also, diagnosis_date is between
            date_of_birth and audit_start_date.

        - setting random diagnosis date so it is before audit_start_date

        - Visit dates are spread evenly throughout each quarter of the audit
            period. For each Visit, the date is randomly set within its
            quarter's date range.
    """

    # Set necessary attributes to calibrate all dates
    DATE_IN_AUDIT = date(2024, 4, 1)
    audit_start_date, audit_end_date = get_audit_period_for_date(DATE_IN_AUDIT)
    fake_patient_creator = FakePatientCreator(
        audit_start_date=audit_start_date,
        audit_end_date=audit_end_date,
    )
    age_range = AgeRange.AGE_0_4

    # Build fake patient instances
    pts = fake_patient_creator.build_fake_patients(
        n=10,
        age_range=age_range,
        # Can additionally pass in extra PatientFactory kwargs here
        postcode="fake_postcode",
    )

    # Build fake Visit instances for each patient
    VISIT_TYPES = generate_random_visit_types(n=12)
    visits = fake_patient_creator.build_fake_visits(
        patients=pts,
        visit_types=VISIT_TYPES,
        hb1ac_target_range=HbA1cTargetRange.WELL_ABOVE,
        age_range=age_range,
        # Can additionally pass in extra VisitFactory kwargs here
        is_valid=True,
    )

    assert len(pts) == 10
    assert len(visits) == 120  # 10 patients * 12 visits
```
