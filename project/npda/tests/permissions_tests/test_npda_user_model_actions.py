"""
Tests for NPDAUser model actions.

- NPDAUser can be created if a valid email, role and PDU are provided.
- NPDAUser cannot be created if an invalid email is provided.
- NPDAUser cannot be created if an invalid role is provided (incorrect key).
- NPDAUser cannot be created if an invalid PDU is provided.
- NPDAUser can be updated if a valid email, role and PDU are provided.
- NPDAUser cannot be updated if an invalid email is provided.
- NPDAUser cannot be updated if an invalid role is provided (incorrect key).
- NPDAUser cannot be updated if an invalid PDU is provided.
- NPDAUser cannot be deleted.
- NPDAUser can be deactivated.
- NPDAUser can be reactivated.
"""

import logging
from http import HTTPStatus

# Python imports
import pytest
# 3rd party imports
from django.urls import reverse

from project.constants.user import RCPCH_AUDIT_TEAM
# E12 imports
from project.npda.models import NPDAUser
from project.npda.tests.utils import login_and_verify_user

logger = logging.getLogger(__name__)

ALDER_HEY_PZ_CODE = "PZ074"

GOSH_PZ_CODE = "PZ196"


def check_all_users_in_pdu(user, users, pz_code):
    for user in users:
        pz_codes = [org["pz_code"] for org in user.organisation_employers.values()]

        if not pz_code in pz_codes:
            pytest.fail(
                f"{user} in {pz_code} should not be able to see {user} in {pz_codes}"
            )


@pytest.mark.django_db
def test_npda_user_list_view_users_can_only_see_users_from_their_pdu(
    seed_groups_fixture,
    seed_users_fixture,
    seed_patients_fixture,
    client,
):
    """Except for RCPCH_AUDIT_TEAM, users should only see users from their own PDU."""

    ah_users = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    )
    # Check there are users from outside Alder Hey so this test doesn't pass by accident
    non_ah_users = NPDAUser.objects.exclude(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    )
    assert non_ah_users.count() > 0

    ah_user = ah_users.first()

    client = login_and_verify_user(client, ah_user)

    url = reverse("npda_users")
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK

    users = response.context_data["object_list"]
    check_all_users_in_pdu(ah_user, users, ALDER_HEY_PZ_CODE)


@pytest.mark.django_db
def test_npda_user_list_view_rcpch_audit_team_can_view_all_users(
    seed_groups_fixture,
    seed_users_fixture,
    seed_patients_fixture,
    client,
):
    """RCPCH_AUDIT_TEAM users can view all users."""

    ah_users = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    )
    # Check there are users from outside Alder Hey so this test doesn't pass by accident
    non_ah_users = NPDAUser.objects.exclude(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    )
    assert non_ah_users.count() > 0

    ah_audit_team_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE,
        role=RCPCH_AUDIT_TEAM,
    ).first()

    client = login_and_verify_user(client, ah_audit_team_user)

    url = reverse("npda_users")

    # The user still defaults to seeing users from just their PDU
    # This is the request made when you click the "All" button on the switcher in the UI
    set_view_preference_response = client.post(
        url, {"view_preference": 2}, headers={"HX-Request": "true"}
    )

    assert set_view_preference_response.status_code == HTTPStatus.OK

    response = client.get(url)
    assert response.status_code == HTTPStatus.OK

    users = response.context_data["object_list"]
    assert users.count() > ah_users.count()


@pytest.mark.django_db
@pytest.mark.skip(
    reason="This test is failing organisations have been removed and we nolonger use ods_code in view preference"
)
def test_npda_user_list_view_users_cannot_switch_outside_their_organisation(
    seed_groups_fixture,
    seed_users_fixture,
    seed_patients_fixture,
    client,
):
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()
    client = login_and_verify_user(client, ah_user)

    url = reverse("npda_users")

    set_view_preference_response = client.post(
        url,
        {"npdauser_ods_code_select_name": GOSH_ODS_CODE},
        headers={"HX-Request": "true"},
    )

    assert set_view_preference_response.status_code == HTTPStatus.FORBIDDEN

    # Check the session isn't modified anyway
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK

    users = response.context_data["object_list"]
    check_all_users_in_pdu(ah_user, users, ALDER_HEY_PZ_CODE)


@pytest.mark.django_db
def test_npda_user_list_view_users_cannot_switch_outside_their_pdu(
    seed_groups_fixture,
    seed_users_fixture,
    seed_patients_fixture,
    client,
):
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()
    client = login_and_verify_user(client, ah_user)

    url = reverse("npda_users")

    set_view_preference_response = client.post(
        url,
        {"npdauser_pz_code_select_name": GOSH_PZ_CODE},
        headers={"HX-Request": "true"},
    )

    assert set_view_preference_response.status_code == HTTPStatus.FORBIDDEN

    # Check the session isn't modified anyway
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK

    users = response.context_data["object_list"]
    check_all_users_in_pdu(ah_user, users, ALDER_HEY_PZ_CODE)


@pytest.mark.django_db  # https://github.com/rcpch/national-paediatric-diabetes-audit/issues/189
def test_npda_user_list_view_normal_users_cannot_set_their_view_preference_to_national(
    seed_groups_fixture,
    seed_users_fixture,
    seed_patients_fixture,
    client,
):
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()
    client = login_and_verify_user(client, ah_user)

    url = reverse("npda_users")

    set_view_preference_response = client.post(
        url, {"view_preference": 2}, headers={"HX-Request": "true"}
    )

    assert set_view_preference_response.status_code == HTTPStatus.FORBIDDEN

    # Check the session isn't modified anyway
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK

    users = response.context_data["object_list"]
    check_all_users_in_pdu(ah_user, users, ALDER_HEY_PZ_CODE)
