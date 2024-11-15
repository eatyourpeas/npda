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

    body = {
        "measurement_method": measurement_method,
        "birth_date": birth_date,
        "observation_date": observation_date,
        "observation_value": observation_value,
        "sex": sex,
        "gestation_weeks": 40,
        "gestation_days": 0,
    }

    ERROR_STRING = "An error occurred while fetching centile and z score details."
    try:
        response = requests.post(url=url, data=body, timeout=10)
        response.raise_for_status()
    except HTTPError as http_err:
        logger.error(
            f"HTTP error occurred fetching organisation details from {url=}: {http_err.response.text}"
        )
        return {"error": ERROR_STRING}
    except Exception as err:
        logger.error(
            f"An error occurred fetching organisation details from {url=}: {err}"
        )
        return {"error": ERROR_STRING}

    return (
        response.json()["measurement_calculated_measurements"]["corrected_centile"],
        response.json()["measurement_calculated_measurements"]["corrected_sds"],
    )


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
    return round(weight / (height / 100) ** 2, 1)
