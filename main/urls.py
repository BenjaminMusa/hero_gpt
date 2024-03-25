from django.urls import path
from . import views


urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("home/", views.home_view, name="home"),
    path("rephrase/<int:id>/", views.rephase_essay_view, name="rephrase"),
    path("profile/", views.profile_view, name="profile"),
    path("service/", views.service_view, name="service"),
    path("home/", views.contact_view, name="contact"),
    path("logout_redirect/", views.logout_redirect_view, name="logout_redirect"),
    path("cancel_sub/<str:id>/", views.cancel_sub, name="cancel_sub"),
]
