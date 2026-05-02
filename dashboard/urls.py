from django.urls import path

from dashboard.views import FinanceSummaryView, OverviewView, ScheduleView, TechnicianDetailView


urlpatterns = [
    path("overview/", OverviewView.as_view(), name="dashboard-overview"),
    path("technicians/<int:pk>/", TechnicianDetailView.as_view(), name="dashboard-technician-detail"),
    path("schedule/", ScheduleView.as_view(), name="dashboard-schedule"),
    path("finance-summary/", FinanceSummaryView.as_view(), name="dashboard-finance-summary"),
]
