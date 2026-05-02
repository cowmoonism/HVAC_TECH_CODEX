from decimal import Decimal

from django.db import models
from django.utils import timezone

from calendar_sync.models import CalendarEvent
from technicians.models import Technician


class PaymentType(models.TextChoices):
    CASH = "CASH", "Cash"
    CHECK = "CHECK", "Check"
    ZELLE = "ZELLE", "Zelle"
    CREDIT_CARD = "CREDIT_CARD", "Credit Card"
    DEBIT_CARD = "DEBIT_CARD", "Debit Card"
    FINANCING = "FINANCING", "Financing"
    GROUPON = "GROUPON", "Groupon"
    ESTIMATE = "ESTIMATE", "Estimate"
    CANCEL = "CANCEL", "Cancel"
    OTHER = "OTHER", "Other"


class ClosedBy(models.TextChoices):
    TECHNICIAN = "TECHNICIAN", "Technician"
    MANAGER = "MANAGER", "Manager"
    CALL_CENTER = "CALL_CENTER", "Call Center"
    CUSTOMER = "CUSTOMER", "Customer"
    OTHER = "OTHER", "Other"


class ReviewStatus(models.TextChoices):
    YES = "YES", "Yes"
    NO = "NO", "No"
    N_A = "N_A", "N/A"


class WorkReport(models.Model):
    technician = models.ForeignKey(
        Technician,
        on_delete=models.CASCADE,
        related_name="work_reports",
    )
    calendar_event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.SET_NULL,
        related_name="work_reports",
        null=True,
        blank=True,
    )
    report_date = models.DateField()
    job_number = models.CharField(max_length=64, blank=True)
    building_number = models.CharField(max_length=64, blank=True)
    address = models.TextField(blank=True)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    closed_by = models.CharField(max_length=20, choices=ClosedBy.choices)
    project_description = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    groupon_review = models.CharField(
        max_length=10,
        choices=ReviewStatus.choices,
        default=ReviewStatus.N_A,
    )
    google_review = models.CharField(
        max_length=10,
        choices=ReviewStatus.choices,
        default=ReviewStatus.N_A,
    )
    yearly_maintenance_plan = models.CharField(
        max_length=10,
        choices=ReviewStatus.choices,
        default=ReviewStatus.N_A,
    )
    submitted_by_telegram_user_id = models.BigIntegerField(null=True, blank=True)
    submitted_from_chat_id = models.BigIntegerField(null=True, blank=True)
    raw_submission = models.JSONField(default=dict, blank=True)
    telegram_sent_at = models.DateTimeField(null=True, blank=True)
    calendar_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]
        indexes = [
            models.Index(fields=["technician", "report_date"]),
            models.Index(fields=["calendar_event"]),
            models.Index(fields=["payment_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        job_label = self.job_number or "No job number"
        return f"{self.technician} - {job_label} - {self.report_date}"

    def normalize_amount(self) -> None:
        if self.payment_type in {PaymentType.ESTIMATE, PaymentType.CANCEL}:
            self.amount = Decimal("0.00")

    def save(self, *args, **kwargs):
        self.normalize_amount()
        super().save(*args, **kwargs)

    def build_telegram_message(self) -> str:
        lines = [
            "Job Report Submitted",
            f"Technician: {self.technician}",
            f"Date: {self.report_date}",
            f"Job Number: {self.job_number or 'N/A'}",
            f"Building Number: {self.building_number or 'N/A'}",
            f"Address: {self.address or 'N/A'}",
            f"Payment Type: {self.get_payment_type_display()}",
            f"Amount: ${self.amount:.2f}",
            f"Closed By: {self.get_closed_by_display()}",
            f"Project Description: {self.project_description or 'N/A'}",
            f"Comments: {self.comments or 'N/A'}",
            f"Groupon Review: {self.get_groupon_review_display()}",
            f"Google Review: {self.get_google_review_display()}",
            f"Yearly Maintenance Plan: {self.get_yearly_maintenance_plan_display()}",
        ]
        if self.calendar_event_id:
            lines.insert(3, f"Calendar Event: {self.calendar_event.title}")
        return "\n".join(lines)

    def build_calendar_description_block(self) -> str:
        submitted_at = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M %Z")
        return "\n".join(
            [
                "--- Work Report Submitted ---",
                f"Report submitted at: {submitted_at}",
                f"Technician: {self.technician}",
                f"Job number: {self.job_number or 'N/A'}",
                f"Payment type: {self.get_payment_type_display()}",
                f"Amount: ${self.amount:.2f}",
                f"Closed by: {self.get_closed_by_display()}",
                f"Project description: {self.project_description or 'N/A'}",
                f"Comments: {self.comments or 'N/A'}",
                f"Groupon review: {self.get_groupon_review_display()}",
                f"Google review: {self.get_google_review_display()}",
                f"Yearly maintenance plan: {self.get_yearly_maintenance_plan_display()}",
            ]
        )
