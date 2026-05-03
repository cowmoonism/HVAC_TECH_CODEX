from rest_framework import serializers

from reports.models import WorkReport
from technicians.validators import MAX_TEXT_LENGTH, validate_non_negative_amount


class WorkReportSerializer(serializers.ModelSerializer):
    technician_display_name = serializers.SerializerMethodField()
    calendar_event_title = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    project_description = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH)
    comments = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH)

    class Meta:
        model = WorkReport
        fields = (
            "id",
            "technician",
            "technician_display_name",
            "calendar_event",
            "calendar_event_title",
            "report_date",
            "job_number",
            "building_number",
            "address",
            "payment_type",
            "amount",
            "closed_by",
            "project_description",
            "comments",
            "groupon_review",
            "google_review",
            "yearly_maintenance_plan",
            "submitted_by_telegram_user_id",
            "submitted_from_chat_id",
            "raw_submission",
            "telegram_sent_at",
            "calendar_updated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "technician_display_name",
            "calendar_event_title",
            "telegram_sent_at",
            "calendar_updated_at",
            "created_at",
            "updated_at",
        )

    def get_technician_display_name(self, obj):
        return str(obj.technician)

    def get_calendar_event_title(self, obj):
        if not obj.calendar_event_id:
            return None
        return obj.calendar_event.title

    def validate_amount(self, value):
        return validate_non_negative_amount(value)
