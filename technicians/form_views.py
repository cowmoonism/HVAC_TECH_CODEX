from django.conf import settings
from django.shortcuts import render

from contracts.models import CleaningProjectType, PaymentProcessingType
from expenses.models import ExpenseType
from reports.models import ClosedBy, PaymentType, ReviewStatus


def _base_context(request, title, endpoint):
    submission_token = request.GET.get("submission_token", "")
    telegram_group_chat_id = request.GET.get("telegram_group_chat_id", "")
    return {
        "title": title,
        "endpoint": endpoint,
        "telegram_user_id": request.GET.get("telegram_user_id", ""),
        "telegram_group_chat_id": telegram_group_chat_id,
        "submission_token": submission_token,
        "insecure_secret_warning": (
            "Production submissions are authenticated with Telegram WebApp initData. "
            "Local DEBUG mode can still use the shared-secret fallback outside Telegram."
        ),
    }


def technician_app(request):
    context = _base_context(request, "Technician App", "")
    return render(request, "technicians/forms/app.html", context)


def report_form(request):
    context = _base_context(request, "Submit Job Report", "/api/technician/submit-work-report/")
    context.update(
        {
            "payment_types": PaymentType.choices,
            "closed_by_choices": ClosedBy.choices,
            "review_statuses": ReviewStatus.choices,
        }
    )
    return render(request, "technicians/forms/report.html", context)


def expense_form(request):
    context = _base_context(request, "Submit Expense", "/api/technician/submit-expense/")
    context["expense_types"] = ExpenseType.choices
    return render(request, "technicians/forms/expense.html", context)


def contract_form(request):
    context = _base_context(request, "Receipt / Contract", "/api/technician/submit-contract/")
    context["project_types"] = CleaningProjectType.choices
    context["payment_processing_types"] = PaymentProcessingType.choices
    return render(request, "technicians/forms/contract.html", context)
