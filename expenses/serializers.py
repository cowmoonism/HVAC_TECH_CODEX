from rest_framework import serializers

from expenses.models import ExpenseReport


class ExpenseReportSerializer(serializers.ModelSerializer):
    technician_display_name = serializers.SerializerMethodField()
    calendar_event_title = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseReport
        fields = (
            "id",
            "technician",
            "technician_display_name",
            "calendar_event",
            "calendar_event_title",
            "expense_date",
            "expense_type",
            "amount",
            "description",
            "receipt_photo_url",
            "submitted_by_telegram_user_id",
            "submitted_from_chat_id",
            "raw_submission",
            "telegram_sent_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "technician_display_name",
            "calendar_event_title",
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
