"""conftest.py
Configures pytest fixtures for npda app tests.
"""

# standard imports

import logging
# third-party imports
from datetime import date
from unittest.mock import patch

import pytest
from pytest_factoryboy import register

# rcpch imports
from project.npda.tests.factories import (NPDAUserFactory,
                                          OrganisationEmployerFactory,
                                          PaediatricsDiabetesUnitFactory,
                                          PatientFactory, TransferFactory,
                                          VisitFactory, seed_groups_fixture,
                                          seed_patients_fixture,
                                          seed_users_fixture)

logger = logging.getLogger(__name__)
# register factories to be used across test directory

# factory object becomes lowercase-underscore form of the class name
register(PatientFactory)  # => patient_factory
register(VisitFactory)  # => patient_visit_factory
register(NPDAUserFactory)  # => npdauser_factory
register(OrganisationEmployerFactory)  # => npdauser_factory
register(PaediatricsDiabetesUnitFactory)  # => npdauser_factory
register(TransferFactory)  # => npdauser_factory

@pytest.fixture
def AUDIT_START_DATE():
    """AUDIT_START_DATE is Day 2 of the first audit period"""
    return date(year=2024, month=4, day=1)

@pytest.fixture
def AUDIT_END_DATE():
    """AUDIT_END_DATE"""
    return date(year=2025, month=3, day=31)