# python
import logging
import requests

# django
from django.conf import settings
from django.contrib.gis.geos import Point

# third party libraries
import httpx

# npda imports
logger = logging.getLogger(__name__)


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


def location_for_postcode(postcode: str):
    # update the longitude and latitude
    """
    The SRID (Spatial Reference System Identifier) 27700 refers to the British National Grid (BNG), a common system used for mapping in the UK. It uses Eastings and Northings, rather than longitude & latitude.
    This system is different from the more common geographic coordinate systems like WGS 84 (SRID 4326), which is used by most global datasets including GPS and many web APIs.
    Coordinates from the ONS data therefore need transforming from WGS 84 (SRID 4326) to British National Grid (SRID 27700).
    Both are included here and stored in the model, as the shape files for the UK health boundaries are produced as BNG, rather than WGS84.
    """
    try:
        # If the postcode begins with JE, it is a Jersey postcode. Skip the coordinates lookup.
        if postcode.lower().startswith("je"):
            location_wgs84 = None
            location_bng = None

        # Fetch the coordinates (WGS 84)
        lon, lat = coordinates_for_postcode(postcode=postcode)

        # Create a Point in WGS 84
        point_wgs84 = Point(lon, lat, srid=4326)
        # Assign the transformed point to location
        location_wgs84 = point_wgs84

        # Transform to British National Grid (SRID 27700) - this has Eastings and Northings, rather than longitude and latitude.
        point_bng = point_wgs84.transform(27700, clone=True)

        # Assign the transformed point to location
        location_bng = point_bng

    except Exception as error:
        lon = None
        lat = None
        location_wgs84 = None
        location_bng = None
        logger.exception(f"Cannot get longitude and latitude for {postcode}: {error}")
        pass

    return lon, lat, location_wgs84, location_bng


def coordinates_for_postcode(postcode: str) -> bool:
    """
    Returns longitude and latitude for a valid postcode.
    """

    # check against API
    response = requests.get(
        url=f"{settings.POSTCODES_IO_API_URL}/postcodes/{postcode}",
        headers={"Ocp-Apim-Subscription-Key": settings.POSTCODES_IO_API_KEY},
        timeout=10,  # times out after 10 seconds
    )

    if response.status_code == 200:
        location = response.json()["result"]
        return location["longitude"], location["latitude"]

    # Only other possibility should be 404, but handle any other status code
    logger.error(
        f"Postcode validation failure. Could not validate postcode at {settings.POSTCODES_IO_API_URL}. {response.status_code=}"
    )
    return None
