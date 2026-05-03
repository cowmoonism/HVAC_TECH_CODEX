from django.urls import path

from technicians.bot_registration_views import (
    ClaimTelegramRegistrationView,
    CompleteTelegramRegistrationView,
)


urlpatterns = [
    path("claim-registration/", ClaimTelegramRegistrationView.as_view(), name="technician-bot-claim-registration"),
    path("complete-registration/", CompleteTelegramRegistrationView.as_view(), name="technician-bot-complete-registration"),
]
