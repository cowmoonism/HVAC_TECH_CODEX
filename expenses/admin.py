from django.contrib import admin

from expenses.models import ExpenseReport


@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    list_display = (
        "technician",
        "expense_date",
        "expense_type",
        "amount",
        "calendar_event",
        "created_at",
    )
    list_filter = ("expense_type", "expense_date")
    search_fields = (
        "technician__display_name",
        "technician__first_name",
        "technician__last_name",
        "description",
        "receipt_photo_url",
    )
    readonly_fields = ("telegram_sent_at", "created_at", "updated_at")
    autocomplete_fields = ("technician", "calendar_event")
