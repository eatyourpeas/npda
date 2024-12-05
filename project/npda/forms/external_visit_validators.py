from dataclasses import dataclass
from decimal import Decimal
from datetime import date
import logging

import asyncio
from asgiref.sync import async_to_sync

from django.core.exceptions import ValidationError
from httpx import HTTPError, AsyncClient

from ..general_functions.dgc_centile_calculations import (
    calculate_centiles_z_scores,
    calculate_bmi,
)


logger = logging.getLogger(__name__)


@dataclass
class VisitExternalValidationResult:
    height_centile: Decimal | ValidationError | None
    height_sds: Decimal | ValidationError | None
    weight_centile: Decimal | ValidationError | None
    weight_sds: Decimal | ValidationError | None
    bmi: Decimal | None
    bmi_centile: Decimal | ValidationError | None
    bmi_sds: Decimal | ValidationError | None


# TODO MRB: ensure we round to one decimal place

async def _calculate_centiles_z_scores(
    birth_date: date, observation_date: date, sex: int, measurement_method: str, observation_value: Decimal, async_client: AsyncClient
) -> Decimal | ValidationError | None:
    try:
        centile, sds = await calculate_centiles_z_scores(
            birth_date=birth_date,
            observation_date=observation_date,
            measurement_method=measurement_method,
            observation_value=observation_value,
            sex=sex,
            async_client=async_client,
        )

        # TODO MRB: ensure ValidationError comes if values out of range

        return centile, sds
    except HTTPError as err:
        logger.warning(f"Error calculating centiles and z-scores for {measurement_method} {err}")


# TODO MRB: handle parameters being none


async def validate_visit_async(
    birth_date: date, observation_date: date, sex: int, height: Decimal, weight: Decimal, async_client: AsyncClient
) -> VisitExternalValidationResult:
    ret = VisitExternalValidationResult(None, None, None, None, None, None, None)

    if sex == 1:
        sex = "male"
    elif sex == 2:
        sex = "female"
    else:
        logger.warning(
            "Sex is not known or not specified. Cannot calculate centiles and z-scores."
        )
        return ret

    bmi = round(calculate_bmi(height, weight), 1)
    ret.bmi = bmi

    validate_height_task = _calculate_centiles_z_scores(birth_date, observation_date, sex, "height", height, async_client)
    validate_weight_task = _calculate_centiles_z_scores(birth_date, observation_date, sex, "weight", weight, async_client)
    validate_bmi_task = _calculate_centiles_z_scores(birth_date, observation_date, sex, "bmi", bmi, async_client)

    # This is the Python equivalent of Promise.allSettled
    # Run all the lookups in parallel but retain exceptions per job rather than returning the first one
    [height_result, weight_result, bmi_result] = (
        await asyncio.gather(
            validate_height_task,
            validate_weight_task,
            validate_bmi_task,
            return_exceptions=True,
        )
    )

    if isinstance(height_result, Exception) and not type(height_result) is ValidationError:
        raise height_result
    elif type(height_result) is ValidationError:
        ret.height_centile = height_result
        ret.height_sds = height_result
    else:
        (height_centile, height_sds) = height_result

        ret.height_centile = height_centile
        ret.height_sds = height_sds
    
    if isinstance(weight_result, Exception) and not type(weight_result) is ValidationError:
        raise weight_result
    elif type(weight_result) is ValidationError:
        ret.weight_centile = height_result
        ret.weight_sds = height_result
    else:
        (weight_centile, weight_sds) = weight_result
        
        ret.weight_centile = weight_centile
        ret.weight_sds = weight_sds
    
    if isinstance(bmi_result, Exception) and not type(bmi_result) is ValidationError:
        raise bmi_result
    elif type(bmi_result) is ValidationError:
        ret.weight_centile = bmi_result
        ret.weight_sds = bmi_result
    else:
        (bmi_centile, bmi_sds) = bmi_result
        
        ret.bmi_centile = bmi_centile
        ret.bmi_sds = bmi_sds

    return ret


def validate_visit_sync(
    birth_date: date, observation_date: date, sex: int, height: Decimal, weight: Decimal
) -> VisitExternalValidationResult:
    async def wrapper():
        async with AsyncClient() as client:
            ret = await validate_visit_async(birth_date, observation_date, sex, height, weight, client)
            return ret

    return async_to_sync(wrapper)()