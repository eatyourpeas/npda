# python
import logging
from typing import Optional

# django
from django.conf import settings

# third party libraries
import httpx

# npda imports

# Logging
logger = logging.getLogger(__name__)


async def gp_ods_code_for_postcode(postcode: str, async_client: httpx.AsyncClient) -> Optional[str]:
    """
    Returns GP practice as an object from NHS API against a postcode
    """

    url = settings.NHS_SPINE_SERVICES_URL
    request_url = (
        f"{url}/organisations?PostCode={postcode}&Status=Active&PrimaryRoleId=RO177"
    )

    response = await async_client.get(
        url=request_url,
        timeout=10,  # times out after 10 seconds
    )
    response.raise_for_status()

    organisations = response.json()["Organisations"]

    if len(organisations) > 0:
        return organisations[0]["OrgId"]


async def gp_details_for_ods_code(ods_code: str, async_client: httpx.AsyncClient) -> Optional[dict]:
    """
    Returns address, name and long/lat for ods code
    """

    url = f"{settings.NHS_SPINE_SERVICES_URL}/organisations/{ods_code}"

    response = await async_client.get(
        url=url,
        timeout=10,  # times out after 10 seconds
    )
    
    if response.status_code == 404:
        return None

    response.raise_for_status()

    return response.json()["Organisation"]
