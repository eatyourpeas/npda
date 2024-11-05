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
    use_postcodes_io = settings.POSTCODES_IO_API_URL and settings.POSTCODES_IO_API_KEY

    if use_postcodes_io:
        request_url = f"{settings.POSTCODES_IO_API_URL}/postcodes/{postcode}"
    else:
        request_url = f"{settings.POSTCODE_API_BASE_URL}/postcodes/{postcode}.json"

    response = await async_client.get(
        url=request_url,
        timeout=10,  # times out after 10 seconds
    )
    response.raise_for_status()

    if use_postcodes_io:
        print(f"Postcodes.io response: {response.json()}")
        normalised_postcode = response.json()["result"]["postcode"]
    else:
        normalised_postcode = response.json()["data"]["id"]

    return {
        "normalised_postcode": normalised_postcode
    }