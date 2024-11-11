from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from two_factor.urls import urlpatterns as tf_urls
from .npda.views.npda_users import RCPCHLoginView
from .npda.views import *

# Custom error pages
handler400 = "project.npda.views.error_400"
handler403 = "project.npda.views.error_403"
handler404 = "project.npda.views.error_404"
handler500 = "project.npda.views.error_500"

# OVERRIDE TWO_FACTOR LOGIN URL TO CAPTCHA LOGIN
for item in tf_urls:
    if type(item) == list:
        for url_pattern in item:
            if vars(url_pattern).get("name") == "login":
                url_pattern.callback = RCPCHLoginView.as_view()
        break

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(tf_urls)),
    path("", include("project.npda.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
