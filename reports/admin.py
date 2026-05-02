from django.contrib import admin

from reports.models import WorkReport


@admin.register(WorkReport)
class WorkReportAdmin(admin.ModelAdmin):
    list_display = (
        "technician",
        "report_date",
        "job_number",
        "payment_type",
        "amount",
        "closed_by",
        "created_at",
    )
    list_filter = (
        "payment_type",
        "closed_by",
        "groupon_review",
        "google_review",
        "yearly_maintenance_plan",
        "report_date",
    )
    search_fields = (
        "technician__display_name",
        "technician__first_name",
        "technician__last_name",
        "job_number",
        "building_number",
        "address",
        "project_description",
        "comments",
    )
    readonly_fields = ("telegram_sent_at", "calendar_updated_at", "created_at", "updated_at")
    autocomplete_fields = ("technician", "calendar_event")
