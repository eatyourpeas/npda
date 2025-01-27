"""https://docs.djangoproject.com/en/5.1/topics/http/middleware/"""

from time import time

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect


class AutoLogoutMiddleware:
    """Auto-logout users based"""

    def __init__(self, get_response):
        # One-time configuration and initialization.
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # Only track authenticated users
        if request.user.is_authenticated:

            current_time = time()

            # Initialise last_activity if not set
            if "last_activity" not in request.session:
                request.session["last_activity"] = current_time

            last_activity = request.session.get("last_activity")

            # Check if idle timeout has been exceeded
            idle_time_limit = settings.AUTO_LOGOUT_IDLE_TIME_SECONDS

            if (current_time - last_activity) > idle_time_limit:
                logout(request)
                request.session.flush()  # Clear all session data safely
                return redirect(settings.LOGOUT_REDIRECT_URL)

            # Update last activity timestamp
            request.session["last_activity"] = current_time

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
