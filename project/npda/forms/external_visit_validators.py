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
class CentileAndSDS:
    centile: Decimal
    sds: Decimal


@dataclass
class VisitExternalValidationResult:
    height_result: CentileAndSDS | ValidationError | None
    weight_result: CentileAndSDS | ValidationError | None
    bmi: Decimal | None
    bmi_result: CentileAndSDS | ValidationError | None


async def _calculate_centiles_z_scores(
    birth_date: date, observation_date: date, sex: int, measurement_method: str, observation_value: Decimal | None, async_client: AsyncClient
) -> CentileAndSDS | None:
    if observation_value is None:
        logger.warning(
            f"Cannot calculate centiles and z-scores for {measurement_method} as it is missing"
        )
        return None

    try:
        centile, sds = await calculate_centiles_z_scores(
            birth_date=birth_date,
            observation_date=observation_date,
            measurement_method=measurement_method,
            observation_value=observation_value,
            sex=sex,
            async_client=async_client,
        )

        return CentileAndSDS(centile, sds)
    except HTTPError as err:
        logger.warning(f"Error calculating centiles and z-scores for {measurement_method} {err}", exc_info=True)

# TODO: test questionnaire missing height, weight and observation_date. Do we get blank values for them?

async def validate_visit_async(
    birth_date: date | None,
    observation_date: date | None,
    sex: int | None,
    height: Decimal | None,
    weight: Decimal | None,
    async_client: AsyncClient
) -> VisitExternalValidationResult:
    ret = VisitExternalValidationResult(None, None, None, None)

    if not birth_date:
        logger.warning("Birth date is not specified. Cannot calculate centiles and z-scores.")
        return ret

    if not observation_date:
        logger.warning("Observation date is not specified. Cannot calculate centiles and z-scores.")
        return ret

    if sex == 1:
        sex = "male"
    elif sex == 2:
        sex = "female"
    else:
        logger.warning(
            "Sex is not known or not specified. Cannot calculate centiles and z-scores."
        )
        return ret

    bmi = None

    if height is not None and weight is not None:
        bmi = round(calculate_bmi(height, weight), 1)
        ret.bmi = bmi
    else:
        logger.warning(
            "Missing height or weight. Cannot calculate BMI centiles and z-scores."
        )

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

    for [result, result_field] in [
        [height_result, "height_result"],
        [weight_result, "weight_result"],
        [bmi_result, "bmi_result"]
    ]:
        if isinstance(result, Exception) and not type(result) is ValidationError:
            raise result
    
        setattr(ret, result_field, result)

    return ret


def validate_visit_sync(
    birth_date: date,
    observation_date: date | None,
    sex: int | None,
    height: Decimal | None,
    weight: Decimal | None
) -> VisitExternalValidationResult:
    async def wrapper():
        async with AsyncClient() as client:
            ret = await validate_visit_async(birth_date, observation_date, sex, height, weight, client)
            return ret

    return async_to_sync(wrapper)()