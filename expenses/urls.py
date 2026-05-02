from django.urls import include, path
from rest_framework.routers import DefaultRouter

from expenses.views import ExpenseReportViewSet


router = DefaultRouter()
router.register("expense-reports", ExpenseReportViewSet, basename="expense-report")

urlpatterns = [
    path("", include(router.urls)),
]
