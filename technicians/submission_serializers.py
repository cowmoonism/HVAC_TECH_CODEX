from rest_framework import serializers
from rest_framework.exceptions import NotFound

from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from contracts.models import CleaningProjectType, PaymentProcessingType
from contracts.serializers import normalize_card_number, validate_card_csc
from expenses.models import ExpenseType
from reports.models import ClosedBy, PaymentType, ReviewStatus
from technicians.models import Technician
from technicians.validators import (
    MAX_TEXT_LENGTH,
    validate_http_url,
    validate_non_negative_amount,
    validate_telegram_numeric,
)


class TechnicianSubmissionBaseSerializer(serializers.Serializer):
    telegram_user_id = serializers.CharField(max_length=64)
    telegram_group_chat_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    google_event_id = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_telegram_user_id(self, value):
        return validate_telegram_numeric(value, "telegram_user_id")

    def validate_telegram_group_chat_id(self, value):
        return validate_telegram_numeric(value, "telegram_group_chat_id")

    def get_technician(self):
        telegram_user_id = self.validated_data["telegram_user_id"]
        try:
            return Technician.objects.get(telegram_user_id=str(telegram_user_id))
        except Technician.DoesNotExist:
            raise NotFound({"telegram_user_id": f"No technician found for Telegram user id {telegram_user_id}."})

    def find_calendar_event(self, technician, date_field=None, job_number=None):
        google_event_id = self.validated_data.get("google_event_id")
        if google_event_id:
            try:
                return CalendarEvent.objects.get(
                    technician=technician,
                    google_event_id=google_event_id,
                )
            except CalendarEvent.DoesNotExist:
                raise serializers.ValidationError(
                    {"google_event_id": "No matching calendar event found for this technician."}
                )

        if date_field and job_number:
            inactive_statuses = [
                CalendarEventStatus.CANCELED,
                CalendarEventStatus.RESCHEDULED,
                CalendarEventStatus.FAKE,
            ]
            return (
                CalendarEvent.objects.filter(
                    technician=technician,
                    start_at__date=date_field,
                    job_number=job_number,
                    event_type=CalendarEventType.JOB,
                )
                .exclude(status__in=inactive_statuses)
                .order_by("start_at")
                .first()
            )
        return None

    def telegram_metadata(self):
        return {
            "submitted_by_telegram_user_id": int(self.validated_data["telegram_user_id"]),
            "submitted_from_chat_id": self._optional_int(self.validated_data.get("telegram_group_chat_id")),
            "raw_submission": dict(self.initial_data),
        }

    def _optional_int(self, value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError({"telegram_group_chat_id": "Use an integer chat id."})


class TechnicianWorkReportSubmissionSerializer(TechnicianSubmissionBaseSerializer):
    job_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    report_date = serializers.DateField()
    building_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    payment_type = serializers.ChoiceField(choices=PaymentType.choices)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    closed_by = serializers.ChoiceField(choices=ClosedBy.choices)
    project_description = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH)
    comments = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH)
    groupon_review = serializers.ChoiceField(choices=ReviewStatus.choices)
    google_review = serializers.ChoiceField(choices=ReviewStatus.choices)
    yearly_maintenance_plan = serializers.ChoiceField(choices=ReviewStatus.choices)

    def to_service_data(self):
        technician = self.get_technician()
        job_number = self.validated_data.get("job_number", "")
        calendar_event = self.find_calendar_event(
            technician,
            date_field=self.validated_data["report_date"],
            job_number=job_number,
        )
        data = {
            "technician": technician.id,
            "calendar_event": calendar_event.id if calendar_event else None,
            "report_date": self.validated_data["report_date"],
            "job_number": job_number,
            "building_number": self.validated_data.get("building_number", ""),
            "address": self.validated_data.get("address", ""),
            "payment_type": self.validated_data["payment_type"],
            "amount": self.validated_data["amount"],
            "closed_by": self.validated_data["closed_by"],
            "project_description": self.validated_data.get("project_description", ""),
            "comments": self.validated_data.get("comments", ""),
            "groupon_review": self.validated_data["groupon_review"],
            "google_review": self.validated_data["google_review"],
            "yearly_maintenance_plan": self.validated_data["yearly_maintenance_plan"],
        }
        data.update(self.telegram_metadata())
        return data


class TechnicianExpenseSubmissionSerializer(TechnicianSubmissionBaseSerializer):
    expense_date = serializers.DateField()
    expense_type = serializers.ChoiceField(choices=ExpenseType.choices)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH)
    receipt_photo_url = serializers.URLField(required=False, allow_blank=True)

    def validate_amount(self, value):
        return validate_non_negative_amount(value)

    def validate_receipt_photo_url(self, value):
        return validate_http_url(value, "receipt_photo_url")

    def to_service_data(self):
        technician = self.get_technician()
        calendar_event = self.find_calendar_event(technician)
        data = {
            "technician": technician.id,
            "calendar_event": calendar_event.id if calendar_event else None,
            "expense_date": self.validated_data["expense_date"],
            "expense_type": self.validated_data["expense_type"],
            "amount": self.validated_data["amount"],
            "description": self.validated_data.get("description", ""),
            "receipt_photo_url": self.validated_data.get("receipt_photo_url", ""),
        }
        data.update(self.telegram_metadata())
        return data


class TechnicianContractSubmissionSerializer(TechnicianSubmissionBaseSerializer):
    sensitive_submission_fields = {"credit_card_number", "card_csc"}

    contract_date = serializers.DateField()
    customer_name = serializers.CharField(max_length=255)
    customer_address = serializers.CharField()
    customer_phone = serializers.CharField(max_length=32)
    state_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    project_type = serializers.ChoiceField(choices=CleaningProjectType.choices)
    project_description = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    sales_tax = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_processing_type = serializers.ChoiceField(
        choices=PaymentProcessingType.choices,
        required=False,
        allow_blank=True,
    )
    credit_card_number = serializers.CharField(max_length=19, required=False, allow_blank=True)
    credit_card_last4 = serializers.CharField(max_length=4, required=False, allow_blank=True)
    card_exp_date = serializers.CharField(max_length=10, required=False, allow_blank=True)
    card_csc = serializers.CharField(max_length=4, required=False, allow_blank=True)
    billing_zip_code = serializers.CharField(max_length=16, required=False, allow_blank=True)

    def _sanitized_raw_submission(self):
        raw = dict(self.initial_data)
        for field in self.sensitive_submission_fields:
            if field in raw and raw[field]:
                raw[field] = "[REDACTED]"
        return raw

    def to_service_data(self):
        technician = self.get_technician()
        calendar_event = self.find_calendar_event(technician)
        data = {
            "technician": technician.id,
            "calendar_event": calendar_event.id if calendar_event else None,
            "contract_date": self.validated_data["contract_date"],
            "customer_name": self.validated_data["customer_name"],
            "customer_address": self.validated_data["customer_address"],
            "customer_phone": self.validated_data["customer_phone"],
            "state_id": self.validated_data.get("state_id", ""),
            "project_type": self.validated_data["project_type"],
            "project_description": self.validated_data.get("project_description", ""),
            "subtotal": self.validated_data["subtotal"],
            "sales_tax": self.validated_data["sales_tax"],
            "payment_processing_type": self.validated_data.get("payment_processing_type", ""),
            "credit_card_number": self.validated_data.get("credit_card_number", ""),
            "credit_card_last4": self.validated_data.get("credit_card_last4", ""),
            "card_exp_date": self.validated_data.get("card_exp_date", ""),
            "card_csc": self.validated_data.get("card_csc", ""),
            "billing_zip_code": self.validated_data.get("billing_zip_code", ""),
        }
        metadata = self.telegram_metadata()
        metadata["raw_submission"] = self._sanitized_raw_submission()
        data.update(metadata)
        return data

    def validate_subtotal(self, value):
        return validate_non_negative_amount(value, "subtotal")

    def validate_sales_tax(self, value):
        return validate_non_negative_amount(value, "sales_tax")

    def validate_credit_card_number(self, value):
        return normalize_card_number(value)

    def validate_card_csc(self, value):
        return validate_card_csc(value)
