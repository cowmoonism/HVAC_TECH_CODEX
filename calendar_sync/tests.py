from datetime import date, datetime, time

from django.test import TestCase
from django.utils import timezone

from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from calendar_sync.services import build_technician_schedule_message
from technicians.models import Technician


class ScheduleMessageTests(TestCase):
    def setUp(self):
        self.technician = Technician.objects.create(
            first_name="Schedule",
            last_name="Tech",
            display_name="Schedule Tech",
        )
        self.target_date = date(2026, 5, 4)

    def aware_at(self, hour):
        return timezone.make_aware(datetime.combine(self.target_date, time(hour, 0)))

    def test_schedule_message_excludes_inactive_and_early_events(self):
        CalendarEvent.objects.create(
            technician=self.technician,
            google_calendar_id="calendar",
            google_event_id="before-8",
            event_type=CalendarEventType.JOB,
            status=CalendarEventStatus.SCHEDULED,
            title="0. Too Early",
            location="Early Address",
            start_at=self.aware_at(7),
            end_at=self.aware_at(8),
        )
        CalendarEvent.objects.create(
            technician=self.technician,
            google_calendar_id="calendar",
            google_event_id="active",
            event_type=CalendarEventType.JOB,
            status=CalendarEventStatus.SCHEDULED,
            title="1. Duct Cleaning (private) didnt buy",
            location="123 Main St",
            start_at=self.aware_at(9),
            end_at=self.aware_at(11),
        )
        for event_id, status in [
            ("canceled", CalendarEventStatus.CANCELED),
            ("rescheduled", CalendarEventStatus.RESCHEDULED),
            ("fake", CalendarEventStatus.FAKE),
        ]:
            CalendarEvent.objects.create(
                technician=self.technician,
                google_calendar_id="calendar",
                google_event_id=event_id,
                event_type=CalendarEventType.JOB,
                status=status,
                title=f"{event_id.title()} Job",
                location="Filtered Address",
                start_at=self.aware_at(12),
                end_at=self.aware_at(13),
            )

        message = build_technician_schedule_message(self.technician.id, self.target_date)

        self.assertIn("Hi Schedule Tech, here is your schedule for Monday, May 04:", message)
        self.assertIn("9-11", message)
        self.assertIn("123 Main St", message)
        self.assertIn("1. Duct Cleaning", message)
        self.assertNotIn("Too Early", message)
        self.assertNotIn("Canceled Job", message)
        self.assertNotIn("Rescheduled Job", message)
        self.assertNotIn("Fake Job", message)
