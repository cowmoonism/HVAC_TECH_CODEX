import secrets

from django.db import models


class TechnicianStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    SUSPENDED = "SUSPENDED", "Suspended"
    ONBOARDING = "ONBOARDING", "Onboarding"


class TechnicianTelegramRegistrationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CLAIMED = "CLAIMED", "Claimed"
    LINKED = "LINKED", "Linked"
    SUPERSEDED = "SUPERSEDED", "Superseded"


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


class TechnicianTelegramRegistration(models.Model):
    technician = models.ForeignKey(
        Technician,
        on_delete=models.CASCADE,
        related_name="telegram_registrations",
    )
    token = models.CharField(max_length=128, unique=True, editable=False)
    status = models.CharField(
        max_length=20,
        choices=TechnicianTelegramRegistrationStatus.choices,
        default=TechnicianTelegramRegistrationStatus.PENDING,
    )
    telegram_user_id = models.CharField(max_length=64, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    telegram_group_chat_id = models.CharField(max_length=64, blank=True)
    telegram_group_title = models.CharField(max_length=255, blank=True)
    telegram_chat_type = models.CharField(max_length=32, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    linked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["technician", "status"]),
            models.Index(fields=["telegram_user_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.technician} Telegram registration ({self.status})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)
