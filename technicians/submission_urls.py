from django.urls import path

from technicians.submission_views import (
    SubmitContractView,
    SubmitExpenseView,
    SubmitWorkReportView,
    TechnicianCalendarEventsView,
)


urlpatterns = [
    path("calendar-events/", TechnicianCalendarEventsView.as_view(), name="technician-calendar-events"),
    path("submit-work-report/", SubmitWorkReportView.as_view(), name="technician-submit-work-report"),
    path("submit-expense/", SubmitExpenseView.as_view(), name="technician-submit-expense"),
    path("submit-contract/", SubmitContractView.as_view(), name="technician-submit-contract"),
]
