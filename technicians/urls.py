from django.urls import include, path
from rest_framework.routers import DefaultRouter

from technicians.views import TechnicianViewSet


router = DefaultRouter()
router.register("", TechnicianViewSet, basename="technician")

urlpatterns = [
    path("", include(router.urls)),
]
