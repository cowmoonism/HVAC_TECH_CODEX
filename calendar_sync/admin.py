from django.contrib import admin

from calendar_sync.models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "technician",
        "event_type",
        "status",
        "start_at",
        "end_at",
        "google_event_id",
    )
    list_filter = ("event_type", "status", "is_report_required")
    search_fields = (
        "title",
        "location",
        "description",
        "job_number",
        "google_calendar_id",
        "google_event_id",
        "technician__display_name",
        "technician__first_name",
        "technician__last_name",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("technician",)
