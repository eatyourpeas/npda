# python
import logging

# django
from django.conf import settings

# third party libraries
import httpx

# npda imports


async def validate_postcode(postcode: str, async_client: httpx.AsyncClient):
    """
    Tests if postcode is valid, normalising it to AB1 2CD format if it is
    Throws None if the postcode does not exist, otherwise returns the normalised version
    """

    response = await async_client.get(
        url=f"{settings.POSTCODES_IO_API_URL}/postcodes/{postcode}",
        headers={"Ocp-Apim-Subscription-Key": settings.POSTCODES_IO_API_KEY},
        timeout=10,  # times out after 10 seconds
    )

    if response.status_code == 404:
        return None
    
    response.raise_for_status()

    normalised_postcode = response.json()["result"]["postcode"]

    return normalised_postcode
