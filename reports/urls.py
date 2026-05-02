from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reports.views import DailySummaryView, WeeklySummaryView, WorkReportViewSet


router = DefaultRouter()
router.register("work-reports", WorkReportViewSet, basename="work-report")

urlpatterns = [
    path("daily-summary/", DailySummaryView.as_view(), name="reports-daily-summary"),
    path("weekly-summary/", WeeklySummaryView.as_view(), name="reports-weekly-summary"),
    path("", include(router.urls)),
]
