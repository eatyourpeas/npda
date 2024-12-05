import datetime
import json
import logging
import httpx

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


async def calculate_centiles_z_scores(
    birth_date, observation_date, sex, observation_value, measurement_method, async_client
):
    """
    Calculate the centiles and z-scores for height and weight for a given patient.

    :param height: The height of the patient.
    :param weight: The weight of the patient.
    :param birth_date: The birth date of the patient.
    :param observation_date: The observation date of the patient.
    :return: A tuple containing the centiles and z-scores for the requested measurement.
    """

    url = f"{settings.RCPCH_DGC_API_URL}/uk-who/calculation"

    body = {
        "measurement_method": measurement_method,
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "observation_date": observation_date.strftime("%Y-%m-%d"),
        "observation_value": float(observation_value),
        "sex": sex,
        "gestation_weeks": 40,
        "gestation_days": 0,
    }

    response = await async_client.post(
        url=url,
        json=body,
        timeout=10,
        headers={"Subscription-Key": f"{settings.RCPCH_DGC_API_KEY}"},
    )

    if response.status_code == 422:
        msg = response.json()["detail"][0]["msg"]
        raise ValidationError(msg)

    response.raise_for_status()

    data = response.json()

    centile = data["measurement_calculated_values"]["corrected_centile"]
    if centile is not None:
        centile = round(centile, 1)

    z_score = data["measurement_calculated_values"]["corrected_sds"]
    if z_score is not None:
        z_score = round(z_score, 1)

    if centile is not None and centile > 99.9:
        centile = 99.9

    return (centile, z_score)


def calculate_bmi(height, weight):
    """
    Calculate the BMI of a patient.

    :param height: The height of the patient in cm.
    :param weight: The weight of the patient in kg.
    :return: The BMI of the patient.
    """
    bmi = round(weight / (height / 100) ** 2, 1)
    
    if bmi > 99:
        return None
    
    return bmi
