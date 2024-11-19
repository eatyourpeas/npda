import datetime
import json
import logging
import requests
from requests.exceptions import HTTPError
from django.conf import settings

logger = logging.getLogger(__name__)


def calculate_centiles_z_scores(
    birth_date, observation_date, sex, observation_value, measurement_method
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

    # test if any of the parameters are none
    if not all(
        [
            birth_date,
            observation_date,
            sex,
            observation_value,
            measurement_method,
        ]
    ):
        logger.warning(f"Missing parameters in calculate_centiles_z_scores")
        return None, None

    if sex == 1:
        sex = "male"
    elif sex == 2:
        sex = "female"
    elif sex == 9 or sex == 0:
        logger.warning(
            "Sex is not known or not specified. Cannot calculate centiles and z-scores."
        )
        return None, None

    body = {
        "measurement_method": measurement_method,
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "observation_date": observation_date.strftime("%Y-%m-%d"),
        "observation_value": float(observation_value),
        "sex": sex,
        "gestation_weeks": 40,
        "gestation_days": 0,
    }

    ERROR_STRING = "An error occurred while fetching centile and z score details."
    try:
        response = requests.post(url=url, json=body, timeout=10)
        response.raise_for_status()
    except HTTPError as http_err:
        logger.error(f"{ERROR_STRING} Error: http error {http_err.response.text}")
        return None, None
    except Exception as err:
        logger.error(f"{ERROR_STRING} Error: {err}")
        return None, None

    if (
        response.json()["measurement_calculated_values"]["corrected_centile"]
        is not None
    ):
        centile = round(
            response.json()["measurement_calculated_values"]["corrected_centile"], 1
        )
    if response.json()["measurement_calculated_values"]["corrected_sds"] is not None:
        z_score = round(
            response.json()["measurement_calculated_values"]["corrected_sds"], 1
        )

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
    if height < 2:
        raise ValueError("Height must be in cm.")
    if weight > 250:
        raise ValueError("Weight must be in kg.")
    bmi = round(weight / (height / 100) ** 2, 1)
    if bmi > 99:
        return None
    return bmi
