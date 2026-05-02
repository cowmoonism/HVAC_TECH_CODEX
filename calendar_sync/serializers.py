from rest_framework import serializers

from calendar_sync.models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    technician_display_name = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = (
            "id",
            "technician",
            "technician_display_name",
            "google_calendar_id",
            "google_event_id",
            "event_type",
            "status",
            "title",
            "location",
            "description",
            "start_at",
            "end_at",
            "timezone",
            "job_number",
            "is_report_required",
            "last_synced_at",
            "raw_google_payload",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "technician_display_name", "created_at", "updated_at")

    def get_technician_display_name(self, obj):
        return str(obj.technician)
