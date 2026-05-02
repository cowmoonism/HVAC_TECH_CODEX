import re

from django.db import models

from technicians.models import Technician


class CalendarEventType(models.TextChoices):
    JOB = "JOB", "Job"
    PERSONAL_BLOCK = "PERSONAL_BLOCK", "Personal Block"
    INTERNAL_BLOCK = "INTERNAL_BLOCK", "Internal Block"
    OTHER = "OTHER", "Other"


class CalendarEventStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    COMPLETED = "COMPLETED", "Completed"
    CANCELED = "CANCELED", "Canceled"
    RESCHEDULED = "RESCHEDULED", "Rescheduled"
    FAKE = "FAKE", "Fake"
    NO_SHOW = "NO_SHOW", "No Show"


class CalendarEvent(models.Model):
    technician = models.ForeignKey(
        Technician,
        on_delete=models.CASCADE,
        related_name="calendar_events",
    )
    google_calendar_id = models.CharField(max_length=255)
    google_event_id = models.CharField(max_length=255)
    event_type = models.CharField(
        max_length=20,
        choices=CalendarEventType.choices,
        default=CalendarEventType.JOB,
    )
    status = models.CharField(
        max_length=20,
        choices=CalendarEventStatus.choices,
        default=CalendarEventStatus.SCHEDULED,
    )
    title = models.CharField(max_length=255)
    location = models.TextField(blank=True)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    timezone = models.CharField(max_length=64, default="America/Los_Angeles")
    job_number = models.CharField(max_length=64, null=True, blank=True)
    is_report_required = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    raw_google_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at", "technician__last_name", "technician__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["google_calendar_id", "google_event_id"],
                name="unique_google_calendar_event",
            ),
        ]
        indexes = [
            models.Index(fields=["technician", "start_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["google_event_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.technician} ({self.start_at:%Y-%m-%d %H:%M})"

    @property
    def is_active_job(self) -> bool:
        inactive_statuses = {
            CalendarEventStatus.CANCELED,
            CalendarEventStatus.RESCHEDULED,
            CalendarEventStatus.FAKE,
        }
        return self.event_type == CalendarEventType.JOB and self.status not in inactive_statuses

    def clean_title_for_technician(self) -> str:
        title = re.sub(r"\([^)]*\)", " ", self.title)
        title = re.sub(r"\bdidn['’]?t\s+buy\b", " ", title, flags=re.IGNORECASE)
        title = re.sub(r"\bdidnt\s+buy\b", " ", title, flags=re.IGNORECASE)
        return " ".join(title.split())
