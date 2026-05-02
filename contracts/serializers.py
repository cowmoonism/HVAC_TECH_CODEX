from rest_framework import serializers

from contracts.models import ServiceContract


class ServiceContractSerializer(serializers.ModelSerializer):
    technician_display_name = serializers.SerializerMethodField()
    calendar_event_title = serializers.SerializerMethodField()

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
            "credit_card_last4",
            "card_exp_date",
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
