# python imports
import logging
import asyncio

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from asgiref.sync import sync_to_async

# Logging setup
logger = logging.getLogger(__name__)


def login_and_otp_required():
    """
    Must have verified via 2FA
    """

    def check_otp(view, request):
        # Then, ensure 2fa verified
        user = request.user
        # Bypass 2fa if local dev, with warning message
        if settings.DEBUG and user.is_authenticated:
            logger.warning(
                "User %s has bypassed 2FA for %s as settings.DEBUG is %s",
                user,
                view,
                settings.DEBUG,
            )

            return True

        # Prevent unverified users
        if not user.is_verified():
            user_list = user.__dict__
            npda_user = user_list["_wrapped"]
            logger.info(
                "User %s is unverified. Tried accessing %s",
                npda_user,
                view.__qualname__,
            )
            return False

        return True

    def decorator(view):
        async def async_login_and_otp_required(request, *args, **kwargs):
            async_check_otp = sync_to_async(check_otp)

            if await async_check_otp(view, request):
                response = await view(request, *args, **kwargs)
                return response
            else:
                return redirect("two_factor:setup")

        def sync_login_and_otp_required(request, *args, **kwargs):
            if check_otp(view, request):
                return redirect("two_factor:setup")
            else:
                return view(request, *args, **kwargs)

        login_required(view)

        if asyncio.iscoroutinefunction(view):
            print("hello hello")
            return async_login_and_otp_required
        else:
            return sync_login_and_otp_required

    return decorator
