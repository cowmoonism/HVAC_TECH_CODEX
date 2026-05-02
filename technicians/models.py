from django.db import models


class TechnicianStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    SUSPENDED = "SUSPENDED", "Suspended"
    ONBOARDING = "ONBOARDING", "Onboarding"


class Technician(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=TechnicianStatus.choices,
        default=TechnicianStatus.ONBOARDING,
    )
    service_state = models.CharField(max_length=2, blank=True)
    timezone = models.CharField(max_length=64, default="America/Los_Angeles")
    telegram_user_id = models.CharField(max_length=64, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    telegram_group_chat_id = models.CharField(max_length=64, blank=True)
    google_calendar_id = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name", "display_name"]

    def __str__(self) -> str:
        return self.display_name or f"{self.first_name} {self.last_name}".strip()
