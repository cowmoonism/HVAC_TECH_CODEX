from django.conf import settings
from django.db import models


class UserRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    MANAGER = "MANAGER", "Manager"
    DISPATCHER = "DISPATCHER", "Dispatcher"
    CALL_CENTER = "CALL_CENTER", "Call Center"
    ACCOUNTANT = "ACCOUNTANT", "Accountant"
    TECHNICIAN = "TECHNICIAN", "Technician"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.TECHNICIAN,
    )
    phone = models.CharField(max_length=32, blank=True)
    is_active_staff_member = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return f"{self.user.get_username()} ({self.get_role_display()})"
