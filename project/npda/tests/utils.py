# 3rd Party Imports
from django_otp import DEVICE_ID_SESSION_KEY
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from two_factor.utils import default_device

# NPDA Imports


def twofactor_signin(client, test_user) -> None:
    """Helper fn to verify user via 2fa"""
    # OTP ENABLE
    test_user.totpdevice_set.create(name="default")
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = default_device(test_user).persistent_id
    session.save()


def login_and_verify_user(client, user):
    """Helper function to set session attributes for a signed-in user, as done during login."""
    # Log in the user
    client.login(username=user.email, password="pw")

    # # OTP Log in (assumed to be a custom function)
    twofactor_signin(client, user)

    return client
