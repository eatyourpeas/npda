# Python Imports
import logging

# Django Imports
from django.conf import settings

# Third party imports
from celery import shared_task

# Logging setup
logger = logging.getLogger(__name__)


@shared_task
def hello():
    """
    THIS IS A SCHEDULED TASK THAT IS CALLED AT 06:00 EVERY DAY
    THE CRON DATE/FREQUENCY IS SET IN SETTING.PY
    """
    logger.debug("0600 cron check task ran successfully")
