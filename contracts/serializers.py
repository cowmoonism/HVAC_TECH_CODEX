from rest_framework import serializers

from contracts.models import PaymentProcessingType, ServiceContract
from technicians.validators import MAX_TEXT_LENGTH, validate_non_negative_amount


def normalize_card_number(value: str) -> str:
    if value in (None, ""):
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) != 16:
        raise serializers.ValidationError("Enter the full 16-digit card number, or leave this blank.")
    return digits


def validate_card_csc(value: str) -> str:
    if value in (None, ""):
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) not in (3, 4):
        raise serializers.ValidationError("Enter a 3 or 4 digit CSC, or leave this blank.")
    return digits


class ServiceContractSerializer(serializers.ModelSerializer):
    technician_display_name = serializers.SerializerMethodField()
    calendar_event_title = serializers.SerializerMethodField()
    project_description = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    sales_tax = serializers.DecimalField(max_digits=10, decimal_places=2)
    credit_card_number = serializers.CharField(max_length=19, required=False, allow_blank=True, write_only=True)
    card_csc = serializers.CharField(max_length=4, required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ServiceContract
        fields = (
            "id",
            "technician",
            "technician_display_name",
            "calendar_event",
            "calendar_event_title",
            "status",
            "contract_number",
            "contract_date",
            "customer_name",
            "customer_address",
            "customer_phone",
            "state_id",
            "project_type",
            "project_description",
            "subtotal",
            "sales_tax",
            "total",
            "payment_processing_type",
            "credit_card_number",
            "credit_card_last4",
            "card_exp_date",
            "card_csc",
            "billing_zip_code",
            "submitted_by_telegram_user_id",
            "submitted_from_chat_id",
            "pdf_file_url",
            "pdf_generated_at",
            "telegram_sent_at",
            "raw_submission",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "technician_display_name",
            "calendar_event_title",
            "contract_number",
            "total",
            "pdf_generated_at",
            "telegram_sent_at",
            "created_at",
            "updated_at",
        )

    def get_technician_display_name(self, obj):
        return str(obj.technician)

    def get_calendar_event_title(self, obj):
        if not obj.calendar_event_id:
            return None
        return obj.calendar_event.title

    def validate_subtotal(self, value):
        return validate_non_negative_amount(value, "subtotal")

    def validate_sales_tax(self, value):
        return validate_non_negative_amount(value, "sales_tax")

    def validate_payment_processing_type(self, value):
        if value in (None, ""):
            return ""
        if value not in PaymentProcessingType.values:
            raise serializers.ValidationError("Use a valid payment processing type.")
        return value

    def validate_credit_card_number(self, value):
        return normalize_card_number(value)

    def validate_card_csc(self, value):
        return validate_card_csc(value)

    def _pop_sensitive_payment_details(self, validated_data):
        credit_card_number = validated_data.pop("credit_card_number", "")
        card_csc = validated_data.pop("card_csc", "")
        if credit_card_number and not validated_data.get("credit_card_last4"):
            validated_data["credit_card_last4"] = credit_card_number[-4:]
        self._sensitive_payment_details = {
            "credit_card_number": credit_card_number,
            "card_csc": card_csc,
        }

    def create(self, validated_data):
        self._pop_sensitive_payment_details(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._pop_sensitive_payment_details(validated_data)
        return super().update(instance, validated_data)

    def get_sensitive_payment_details(self):
        return getattr(self, "_sensitive_payment_details", {})
