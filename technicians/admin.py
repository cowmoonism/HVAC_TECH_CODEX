from django.contrib import admin

from technicians.models import Technician


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "first_name",
        "last_name",
        "status",
        "service_state",
        "phone",
        "email",
    )
    list_filter = ("status", "service_state")
    search_fields = (
        "first_name",
        "last_name",
        "display_name",
        "phone",
        "email",
        "telegram_username",
    )
    readonly_fields = ("created_at", "updated_at")
