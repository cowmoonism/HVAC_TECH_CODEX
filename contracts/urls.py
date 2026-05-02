from django.urls import include, path
from rest_framework.routers import DefaultRouter

from contracts.views import ServiceContractViewSet


router = DefaultRouter()
router.register("service-contracts", ServiceContractViewSet, basename="service-contract")

urlpatterns = [
    path("", include(router.urls)),
]
