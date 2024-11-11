from django.contrib.auth import urls as auth_urls
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import include, path

from project.npda.forms.npda_user_form import NPDAUpdatePasswordForm
from project.npda.views import (
    PatientListView,
    PatientVisitsListView,
    SubmissionsListView,
    VisitCreateView,
    VisitDeleteView,
    VisitUpdateView,
)

from .views import *

urlpatterns = [
    path("", view=home, name="home"),
    path("home", view=home, name="home"),
    path("view_preference", view=view_preference, name="view_preference"),
    # Submission views
    path(
        "submissions",
        view=SubmissionsListView.as_view(),
        name="submissions",
    ),
    # Patient views
    path(
        "patients",
        view=PatientListView.as_view(),
        name="patients",
    ),
    path("patient/add/", PatientCreateView.as_view(), name="patient-add"),
    path(
        "patient/<int:pk>/update",
        PatientUpdateView.as_view(),
        name="patient-update",
    ),
    path(
        "patient/<int:pk>/delete",
        PatientDeleteView.as_view(),
        name="patient-delete",
    ),
    # Visit views
    path(
        "patient/<int:patient_id>/visits",
        view=PatientVisitsListView.as_view(),
        name="patient_visits",
    ),
    path(
        "patient/<int:patient_id>/visits/create",
        view=VisitCreateView.as_view(),
        name="visit-create",
    ),
    path(
        "patient/<int:patient_id>/visits/<int:pk>/update",
        view=VisitUpdateView.as_view(),
        name="visit-update",
    ),
    path(
        "patient/<int:patient_id>/visits/<int:pk>/delete",
        view=VisitDeleteView.as_view(),
        name="visit-delete",
    ),
    # NPDAUser views
    path("npda_users", view=NPDAUserListView.as_view(), name="npda_users"),
    path("npda_users/add", view=NPDAUserCreateView.as_view(), name="npdauser-create"),
    path(
        "npda_users/<int:npdauser_id>/logs",
        view=NPDAUserLogsListView.as_view(),
        name="npdauser-logs",
    ),
    path(
        "npda_users/<int:pk>/update",
        view=NPDAUserUpdateView.as_view(),
        name="npdauser-update",
    ),
    path(
        "npda_users/<int:pk>/delete",
        view=NPDAUserDeleteView.as_view(),
        name="npdauser-delete",
    ),
    # Authentication -> NOTE: 2FA is implemented in project-level URLS with tf_urls
    path("captcha/", include("captcha.urls")),
    path("account/", include(auth_urls)),
    path(
        "account/password-reset/",
        view=ResetPasswordView.as_view(),
        name="password_reset",
    ),
    path(
        "account/password-reset-confirm/<uidb64>/<token>",
        view=PasswordResetConfirmView.as_view(
            form_class=NPDAUpdatePasswordForm,
            template_name="registration/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    # KPI views
    path(
        "dashboard",
        view=dashboard,
        name="dashboard",
    ),
    path("csrf_fail/", csrf_fail, name="csrf_fail"),
]
