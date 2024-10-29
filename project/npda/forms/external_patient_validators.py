import logging
from dataclasses import dataclass

from asgiref.sync import async_to_sync

from django.core.exceptions import ValidationError
from httpx import HTTPError, AsyncClient

from ..general_functions import (gp_details_for_ods_code,
                                 gp_ods_code_for_postcode,
                                 validate_postcode,
                                 imd_for_postcode)


logger = logging.getLogger(__name__)


@dataclass
class PatientExternalValidationResult:
    postcode: str | ValidationError | None
    gp_practice_ods_code: str | ValidationError | None
    gp_practice_postcode: str | ValidationError | None
    index_of_multiple_deprivation_quintile: str | None 


# Run lookups to external APIs asynchronously to speed up CSV upload by processing patients in parallel
async def validate_patient_async(postcode: str, gp_practice_ods_code: str | None, gp_practice_postcode: str | None, async_client: AsyncClient) -> PatientExternalValidationResult:
    ret = PatientExternalValidationResult(None, None, None, None)

    if postcode:
        try:
            result = await validate_postcode(postcode, async_client)

            if not result:
                ret.postcode = ValidationError(
                    "Invalid postcode %(postcode)s", params={"postcode":postcode}
                )
            else:
                ret.postcode = result["normalised_postcode"]
        except HTTPError as err:
            logger.warning(f"Error validating postcode {err}")
        
        try:
            ret.index_of_multiple_deprivation_quintile = await imd_for_postcode(
                postcode, async_client
            )
        except HTTPError as err:
            logger.warning(
                f"Cannot calculate deprivation score for {postcode} {err}"
            )
    
    if gp_practice_ods_code:
        try:
            # TODO MRB: set gp_practice_postcode based on response (https://github.com/rcpch/national-paediatric-diabetes-audit/issues/330)
            if not await gp_details_for_ods_code(gp_practice_ods_code, async_client):
                ret.gp_practice_ods_code = ValidationError(
                    "Could not find GP practice with ODS code %(ods_code)s",
                    params={"ods_code":gp_practice_ods_code}
                )
            else:
                ret.gp_practice_ods_code = gp_practice_ods_code
        except HTTPError as err:
            logger.warning(f"Error looking up GP practice by ODS code {err}")
    elif gp_practice_postcode:
        try:
            validation_result = await validate_postcode(gp_practice_postcode, async_client)
            normalised_postcode = validation_result["normalised_postcode"]

            ods_code = await gp_ods_code_for_postcode(normalised_postcode, async_client)

            if not ods_code:
                ret.gp_practice_postcode = ValidationError(
                    "Could not find GP practice with postcode %(postcode)s",
                    params={"postcode":gp_practice_postcode}
                )
            else:
                ret.gp_practice_ods_code = ods_code
                ret.gp_practice_postcode = normalised_postcode
        except HTTPError as err:
            logger.warning(f"Error looking up GP practice by postcode {err}")

    return ret

def validate_patient_sync(postcode: str, gp_practice_ods_code: str | None, gp_practice_postcode: str | None) -> PatientExternalValidationResult:
    async def wrapper():
        async with AsyncClient() as client:
            ret = await validate_patient_async(patient_data, client)
            return ret

    return async_to_sync(wrapper)()