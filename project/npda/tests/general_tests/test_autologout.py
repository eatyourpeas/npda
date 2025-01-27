import logging
from datetime import datetime, timedelta
from http import HTTPStatus

# Python imports
import pytest
from django.conf import settings
# 3rd party imports
from django.urls import reverse
from freezegun import freeze_time

from project.constants.user import RCPCH_AUDIT_TEAM
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

    response = client.get(reverse("home"))
    assert response.status_code == HTTPStatus.OK, "User unable to access home"

    # Simulate session expiry with freezegun
    future_time = datetime.now() + timedelta(days=1)
    with freeze_time(future_time):
        response = client.get(reverse("home"))

    assert (
        response.status_code == HTTPStatus.FOUND
    ), f"User not redirected after expected auto-logout; {response.status_code=}"
    assert response.url == reverse(getattr(settings, "LOGIN_REDIRECT_URL", "two_factor:profile"))
