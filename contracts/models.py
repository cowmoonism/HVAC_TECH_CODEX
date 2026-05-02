import secrets
from decimal import Decimal

from django.db import IntegrityError, models
from django.utils import timezone

from calendar_sync.models import CalendarEvent
from technicians.models import Technician


class ContractStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    GENERATED = "GENERATED", "Generated"
    SENT = "SENT", "Sent"
    SIGNED = "SIGNED", "Signed"
    CANCELED = "CANCELED", "Canceled"
    ERROR = "ERROR", "Error"


class CleaningProjectType(models.TextChoices):
    AIR_DUCT_CLEANING = "AIR_DUCT_CLEANING", "Air Duct Cleaning"
    DRYER_VENT_CLEANING = "DRYER_VENT_CLEANING", "Dryer Vent Cleaning"
    CHIMNEY_CLEANING = "CHIMNEY_CLEANING", "Chimney Cleaning"
    HVAC_MAINTENANCE = "HVAC_MAINTENANCE", "HVAC Maintenance"
    OTHER = "OTHER", "Other"


class ServiceContract(models.Model):
    technician = models.ForeignKey(
        Technician,
        on_delete=models.CASCADE,
        related_name="service_contracts",
    )
    calendar_event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.SET_NULL,
        related_name="service_contracts",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
    )
    contract_number = models.CharField(max_length=32, unique=True, blank=True)
    contract_date = models.DateField()
    customer_name = models.CharField(max_length=255)
    customer_address = models.TextField()
    customer_phone = models.CharField(max_length=32)
    state_id = models.CharField(max_length=64, blank=True)
    project_type = models.CharField(max_length=32, choices=CleaningProjectType.choices)
    project_description = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sales_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_date = models.CharField(max_length=10, blank=True)
    billing_zip_code = models.CharField(max_length=16, blank=True)
    submitted_by_telegram_user_id = models.BigIntegerField(null=True, blank=True)
    submitted_from_chat_id = models.BigIntegerField(null=True, blank=True)
    pdf_file_url = models.URLField(blank=True)
    pdf_generated_at = models.DateTimeField(null=True, blank=True)
    telegram_sent_at = models.DateTimeField(null=True, blank=True)
    raw_submission = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-contract_date", "-created_at"]
        indexes = [
            models.Index(fields=["technician", "contract_date"]),
            models.Index(fields=["calendar_event"]),
            models.Index(fields=["status"]),
            models.Index(fields=["contract_number"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.contract_number or 'Unnumbered'} - {self.customer_name}"

    def calculate_total(self) -> Decimal:
        subtotal = Decimal(str(self.subtotal or "0.00"))
        sales_tax = Decimal(str(self.sales_tax or "0.00"))
        self.total = subtotal + sales_tax
        return self.total

    def generate_contract_number(self) -> str:
        if self.contract_number:
            return self.contract_number

        date_value = self.contract_date or timezone.localdate()
        suffix = secrets.token_hex(3).upper()
        self.contract_number = f"HVAC-{date_value:%Y%m%d}-{suffix}"
        return self.contract_number

    def save(self, *args, **kwargs):
        self.calculate_total()
        for attempt in range(5):
            self.generate_contract_number()
            try:
                return super().save(*args, **kwargs)
            except IntegrityError:
                if self.pk or attempt == 4:
                    raise
                self.contract_number = ""

    def build_telegram_message(self) -> str:
        lines = [
            "Service Contract Submitted",
            f"Contract Number: {self.contract_number}",
            f"Status: {self.get_status_display()}",
            f"Technician: {self.technician}",
            f"Date: {self.contract_date}",
            f"Customer: {self.customer_name}",
            f"Phone: {self.customer_phone}",
            f"Address: {self.customer_address}",
            f"Project Type: {self.get_project_type_display()}",
            f"Project Description: {self.project_description or 'N/A'}",
            f"Subtotal: ${self.subtotal:.2f}",
            f"Sales Tax: ${self.sales_tax:.2f}",
            f"Total: ${self.total:.2f}",
        ]
        if self.calendar_event_id:
            lines.insert(5, f"Calendar Event: {self.calendar_event.title}")
        if self.credit_card_last4:
            lines.append(f"Card Last 4: {self.credit_card_last4}")
        return "\n".join(lines)
