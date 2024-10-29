"""
Calculates the index of multiple deprivation for a given postcode
"""

# Standard imports
import logging
import httpx

from asgiref.sync import async_to_sync

# Third party imports
from django.conf import settings

# RCPCH imports

# Logging setup
logger = logging.getLogger(__name__)


async def imd_for_postcode(user_postcode: str, async_client: httpx.AsyncClient) -> int:
    """
    Makes an API call to the RCPCH Census Platform with postcode and quantile_type
    Postcode - can have spaces or not - this is processed by the API
    Quantile - this is an integer representing what quantiles are requested (eg quintile, decile etc)
    """

    response = await async_client.get(
        url=f"{settings.RCPCH_CENSUS_PLATFORM_URL}/index_of_multiple_deprivation_quantile?postcode={user_postcode}&quantile=5",
        headers={"Subscription-Key": f"{settings.RCPCH_CENSUS_PLATFORM_TOKEN}"},
        timeout=10,  # times out after 10 seconds
    )

    if response.status_code != 200:
        logger.error(
            "Could not get deprivation score. Response status %s", response.status_code
        )
        return None

    return response.json()["result"]["data_quantile"]
