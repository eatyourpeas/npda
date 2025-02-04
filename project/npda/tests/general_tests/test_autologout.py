import logging
from datetime import datetime, timedelta
from http import HTTPStatus

# Python imports
import pytest
from django.conf import settings

# 3rd party imports
from django.urls import reverse
from freezegun import freeze_time

# E12 imports
from project.npda.models import NPDAUser
from project.npda.tests.model_tests.test_submissions import ALDER_HEY_PZ_CODE
from project.npda.tests.utils import login_and_verify_user

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_auto_logout_django_auto_logout(
    seed_groups_fixture,
    seed_users_fixture,
    client,
):
    # Get any user
    user = NPDAUser.objects.filter(organisation_employers__pz_code=ALDER_HEY_PZ_CODE).first()

    client = login_and_verify_user(client, user)

    # Try accessing authenticated page
    response = client.get(reverse("dashboard"))
    assert response.status_code == HTTPStatus.OK, "User unable to access home"

    # Simulate session expiry with freezegun
    future_time = (
        datetime.now()
        + timedelta(seconds=settings.AUTO_LOGOUT_IDLE_TIME_SECONDS)
        + timedelta(milliseconds=1)
    )
    with freeze_time(future_time):
        response = client.get(reverse("dashboard"))

    assert (
        response.status_code == HTTPStatus.FOUND
    ), f"User not redirected after expected auto-logout; {response.status_code=}"
    assert response.url == reverse(
        "two_factor:setup"
    ), f"User not redirected to login page ({reverse('two_factor:setup')}), instead to {response.url=}"

    # Finally try to access a protected page, now as an anon user
    response = client.get(reverse("dashboard"))
    assert (
        response.status_code == HTTPStatus.FOUND
    ), f"Anon user tried accessing protected page after autologout, did not receive 302 response; {response.status_code=}"
    assert response.url == reverse(
        "two_factor:setup"
    ), f"User not redirected to login page ({reverse('two_factor:setup')}), instead to {response.url=}"
