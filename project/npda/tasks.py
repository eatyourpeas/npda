# Python Imports
import logging

# Django Imports
from django.conf import settings

# Third party imports
from celery import shared_task

# Project Imports
from .models import Visit
from .forms.visit_form import VisitForm
from .general_functions.csv.csv_upload import validate_visit_async

# Logging setup
logger = logging.getLogger(__name__)


@shared_task
def hello():
    """
    THIS IS A SCHEDULED TASK THAT IS CALLED AT 06:00 EVERY DAY
    THE CRON DATE/FREQUENCY IS SET IN SETTING.PY
    """
    logger.debug("0600 cron check task ran successfully")


# @shared_task
# def validate_visit_using_form(patient_form, row, async_client):
#     fields = row_to_dict(
#         row,
#         Visit,
#     )

#     form = VisitForm(data=fields, initial={"patient": patient_form.instance})
#     # form.async_validation_results = await validate_visit_async(
#     #     birth_date=patient_form.cleaned_data.get("date_of_birth"),
#     #     observation_date=fields["height_weight_observation_date"],
#     #     height=fields["height"],
#     #     weight=fields["weight"],
#     #     sex=patient_form.cleaned_data.get("sex"),
#     #     async_client=async_client,
#     # )

#     return form


@shared_task
def fuck():
    print(
        "FuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuckFuck"
    )
