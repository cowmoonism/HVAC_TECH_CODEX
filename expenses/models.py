from django.db import models

from calendar_sync.models import CalendarEvent
from technicians.models import Technician


class ExpenseType(models.TextChoices):
    GAS = "GAS", "Gas"
    MATERIALS = "MATERIALS", "Materials"
    PARKING = "PARKING", "Parking"
    TOLL = "TOLL", "Toll"
    TOOL = "TOOL", "Tool"
    PARTS = "PARTS", "Parts"
    SUPPLIES = "SUPPLIES", "Supplies"
    OTHER = "OTHER", "Other"


class ExpenseReport(models.Model):
    technician = models.ForeignKey(
        Technician,
        on_delete=models.CASCADE,
        related_name="expense_reports",
    )
    calendar_event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.SET_NULL,
        related_name="expense_reports",
        null=True,
        blank=True,
    )
    expense_date = models.DateField()
    expense_type = models.CharField(max_length=20, choices=ExpenseType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    receipt_photo_url = models.URLField(blank=True)
    submitted_by_telegram_user_id = models.BigIntegerField(null=True, blank=True)
    submitted_from_chat_id = models.BigIntegerField(null=True, blank=True)
    raw_submission = models.JSONField(default=dict, blank=True)
    telegram_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        indexes = [
            models.Index(fields=["technician", "expense_date"]),
            models.Index(fields=["calendar_event"]),
            models.Index(fields=["expense_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.technician} - {self.get_expense_type_display()} - ${self.amount:.2f}"

    def build_telegram_message(self) -> str:
        lines = [
            "Expense Submitted",
            f"Technician: {self.technician}",
            f"Date: {self.expense_date}",
            f"Expense Type: {self.get_expense_type_display()}",
            f"Amount: ${self.amount:.2f}",
            f"Description: {self.description or 'N/A'}",
            f"Receipt Photo: {self.receipt_photo_url or 'N/A'}",
        ]
        if self.calendar_event_id:
            lines.insert(3, f"Calendar Event: {self.calendar_event.title}")
        return "\n".join(lines)
