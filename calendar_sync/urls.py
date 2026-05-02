from django.urls import include, path
from rest_framework.routers import DefaultRouter

from calendar_sync.views import CalendarEventViewSet, SendTechnicianScheduleView, SyncTechnicianCalendarView


router = DefaultRouter()
router.register("events", CalendarEventViewSet, basename="calendar-event")

urlpatterns = [
    path("send-technician-schedule/", SendTechnicianScheduleView.as_view(), name="calendar-send-technician-schedule"),
    path("sync-technician/", SyncTechnicianCalendarView.as_view(), name="calendar-sync-technician"),
    path("", include(router.urls)),
]
