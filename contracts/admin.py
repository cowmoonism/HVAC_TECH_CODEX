from django.contrib import admin

from contracts.models import ServiceContract


@admin.register(ServiceContract)
class ServiceContractAdmin(admin.ModelAdmin):
    list_display = (
        "contract_number",
        "customer_name",
        "technician",
        "status",
        "contract_date",
        "project_type",
        "total",
    )
    list_filter = ("status", "project_type", "contract_date")
    search_fields = (
        "contract_number",
        "customer_name",
        "customer_phone",
        "customer_address",
        "technician__display_name",
        "technician__first_name",
        "technician__last_name",
    )
    readonly_fields = (
        "contract_number",
        "total",
        "pdf_generated_at",
        "telegram_sent_at",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("technician", "calendar_event")
