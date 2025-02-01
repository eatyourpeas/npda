"""
This module contains functions that are used to extract NHS organisations from the RCPCH dataset.
"""

# python imports
import requests
import logging
from typing import Dict, Any, List, Tuple

# django imports
from django.apps import apps
from django.conf import settings

# RCPCH imports


# Logging
logger = logging.getLogger(__name__)


def get_all_pz_codes_with_their_trust_and_primary_organisation() -> (
    List[Tuple[str, str]]
):
    """
    This function returns all NHS organisations from the RCPCH dataset that are affiliated with a paediatric diabetes unit.

    Returns:
        List[Tuple[str, str]]: A list of tuples containing the ODS code and name of NHS organisations.
    """

    request_url = (
        f"{settings.RCPCH_NHS_ORGANISATIONS_API_URL}/paediatric_diabetes_units/parent/"
    )

    headers = {"Ocp-Apim-Subscription-Key": settings.RCPCH_NHS_ORGANISATIONS_API_KEY}

    response = requests.get(request_url, headers=headers, timeout=10)
    response.raise_for_status()

    return response.json()


def fetch_organisation_by_ods_code(ods_code: str) -> Dict[str, Any]:
    """
    This function returns an NHS organisation from the RCPCH dataset that is affiliated with a paediatric diabetes unit.

    Args:
        ods_code (str): The ODS code of the NHS organisation.

    Returns:
        Dict[str, Any]: A dictionary containing the details of the NHS organisation.
    """

    request_url = (
        f"{settings.RCPCH_NHS_ORGANISATIONS_API_URL}/organisations/{ods_code}/"
    )

    headers = {"Ocp-Apim-Subscription-Key": settings.RCPCH_NHS_ORGANISATIONS_API_KEY}

    response = requests.get(request_url, headers=headers, timeout=10)
    response.raise_for_status()

    return response.json()


def fetch_local_authorities_within_radius(
    longitude: float, latitude: float, radius: int
) -> List[str]:
    """
    This function returns all local authorities within a given radius of a point, including boundary geometries.
    """

    request_url = (
        f"{settings.RCPCH_NHS_ORGANISATIONS_API_URL}/local_authority_districts/within_radius/"
        f"?long={longitude}&lat={latitude}&radius={radius}"
    )

    headers = {"Ocp-Apim-Subscription-Key": settings.RCPCH_NHS_ORGANISATIONS_API_KEY}

    response = requests.get(request_url, headers=headers, timeout=10)
    response.raise_for_status()

    return response.json()


def synchronize_pdus_with_rcpch_nhs_organisations():
    """
    This function synchronizes the NHS organisations from the RCPCH dataset with the local database.
    """

    PDU = apps.get_model("npda", "PaediatricDiabetesUnit")
    Organisation = apps.get_model("npda", "Organisation")

    request_url = (
        f"{settings.RCPCH_NHS_ORGANISATIONS_API_URL}/paeidatric_diabetes_units/"
    )

    headers = {"Ocp-Apim-Subscription-Key": settings.RCPCH_NHS_ORGANISATIONS_API_KEY}

    response = requests.get(request_url, headers=headers, timeout=10)
    response.raise_for_status()

    print(response.json())

    # for pz_code, trust in all_pz_codes_with_their_trust_and_primary_organisation:
    #     try:
    #         organisation = Organisation.objects.get(ods_code=pz_code)
    #     except NHSOrganisation.DoesNotExist:
    #         organisation = Organisation(ods_code=pz_code)

    #     organisation.trust = trust
    #     organisation.save()

    #     pdus = PDU.objects.filter(ods_code=pz_code)
    #     for pdu in pdus:
    #         pdu.nhs_organisation = organisation
    #         pdu.save()
