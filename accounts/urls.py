from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import UserProfileViewSet


router = DefaultRouter()
router.register("profiles", UserProfileViewSet, basename="profile")

urlpatterns = [
    path("", include(router.urls)),
]
