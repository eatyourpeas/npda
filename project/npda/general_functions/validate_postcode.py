# python
import logging

# django
from django.conf import settings

# third party libraries
import httpx

# npda imports


async def validate_postcode(postcode: str, async_client: httpx.AsyncClient):
    """
    Tests if postcode is valid
    Returns boolean
    """

    request_url = f"{settings.POSTCODE_API_BASE_URL}/postcodes/{postcode}.json"

    response = await async_client.get(
        url=request_url,
        timeout=10,  # times out after 10 seconds
    )
    response.raise_for_status()

    return {
        "normalised_postcode": response.json()["data"]["id"]
    }