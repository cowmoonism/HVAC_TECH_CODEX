from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserRole
from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from contracts.models import ServiceContract
from dashboard.permissions import DashboardPermission
from expenses.models import ExpenseReport
from reports.models import WorkReport
from technicians.models import Technician, TechnicianStatus
from technicians.serializers import latest_telegram_registration_payload


ZERO = Decimal("0.00")
ZERO_VALUE = Value(ZERO, output_field=DecimalField(max_digits=10, decimal_places=2))


def _user_role(user):
    return getattr(getattr(user, "profile", None), "role", None)


def _is_call_center(user):
    return _user_role(user) == UserRole.CALL_CENTER


def _money(value):
    return f"{value or ZERO:.2f}"


def _parse_date_param(params, name, default=None):
    value = params.get(name)
    if not value:
        return default
    parsed = parse_date(value)
    if parsed is None:
        raise ValidationError({name: "Use YYYY-MM-DD."})
    return parsed


def _active_required_jobs_without_reports():
    inactive_statuses = [
        CalendarEventStatus.CANCELED,
        CalendarEventStatus.RESCHEDULED,
        CalendarEventStatus.FAKE,
    ]
    return (
        CalendarEvent.objects.filter(
            event_type=CalendarEventType.JOB,
            is_report_required=True,
            start_at__lt=timezone.now(),
            work_reports__isnull=True,
        )
        .exclude(status__in=inactive_statuses)
        .distinct()
    )


def _technician_payload(technician):
    return {
        "id": technician.id,
        "first_name": technician.first_name,
        "last_name": technician.last_name,
        "display_name": str(technician),
        "phone": technician.phone,
        "email": technician.email,
        "status": technician.status,
        "service_state": technician.service_state,
        "timezone": technician.timezone,
        "telegram_user_id": technician.telegram_user_id,
        "telegram_username": technician.telegram_username,
        "telegram_group_chat_id": technician.telegram_group_chat_id,
        "google_calendar_id": technician.google_calendar_id,
        "notes": technician.notes,
    }


def _calendar_event_payload(event):
    return {
        "id": event.id,
        "technician": event.technician_id,
        "technician_display_name": str(event.technician),
        "event_type": event.event_type,
        "status": event.status,
        "title": event.title,
        "location": event.location,
        "description": event.description,
        "start_at": event.start_at,
        "end_at": event.end_at,
        "timezone": event.timezone,
        "job_number": event.job_number,
        "is_report_required": event.is_report_required,
    }


def _work_report_payload(report, include_money=True):
    payload = {
        "id": report.id,
        "report_date": report.report_date,
        "job_number": report.job_number,
        "building_number": report.building_number,
        "address": report.address,
        "closed_by": report.closed_by,
        "project_description": report.project_description,
        "comments": report.comments,
        "groupon_review": report.groupon_review,
        "google_review": report.google_review,
        "yearly_maintenance_plan": report.yearly_maintenance_plan,
        "created_at": report.created_at,
    }
    if include_money:
        payload.update(
            {
                "payment_type": report.payment_type,
                "amount": _money(report.amount),
            }
        )
    return payload


def _expense_payload(expense):
    return {
        "id": expense.id,
        "expense_date": expense.expense_date,
        "expense_type": expense.expense_type,
        "amount": _money(expense.amount),
        "description": expense.description,
        "receipt_photo_url": expense.receipt_photo_url,
        "created_at": expense.created_at,
    }


def _contract_payload(contract):
    return {
        "id": contract.id,
        "status": contract.status,
        "contract_number": contract.contract_number,
        "contract_date": contract.contract_date,
        "customer_name": contract.customer_name,
        "customer_address": contract.customer_address,
        "customer_phone": contract.customer_phone,
        "project_type": contract.project_type,
        "subtotal": _money(contract.subtotal),
        "sales_tax": _money(contract.sales_tax),
        "total": _money(contract.total),
        "pdf_file_url": contract.pdf_file_url,
        "pdf_generated_at": contract.pdf_generated_at,
        "created_at": contract.created_at,
    }


class OverviewView(APIView):
    permission_classes = [DashboardPermission]
    dashboard_endpoint = "overview"

    def get(self, request):
        today = timezone.localdate()
        data = {
            "active_technicians_count": Technician.objects.filter(status=TechnicianStatus.ACTIVE).count(),
            "today_events_count": CalendarEvent.objects.filter(start_at__date=today).count(),
            "pending_reports_count": _active_required_jobs_without_reports().count(),
            "contracts_generated_today_count": ServiceContract.objects.filter(pdf_generated_at__date=today).count(),
        }
        if not _is_call_center(request.user):
            data.update(
                {
                    "today_reported_revenue": _money(
                        WorkReport.objects.filter(report_date=today).aggregate(total=Sum("amount"))["total"]
                    ),
                    "today_expenses_total": _money(
                        ExpenseReport.objects.filter(expense_date=today).aggregate(total=Sum("amount"))["total"]
                    ),
                }
            )
        return Response(data)


class TechnicianDetailView(APIView):
    permission_classes = [DashboardPermission]
    dashboard_endpoint = "technician_detail"

    def get(self, request, pk):
        technician = get_object_or_404(Technician, pk=pk)
        now = timezone.now()
        end = now + timedelta(days=7)
        include_money = not _is_call_center(request.user)

        data = {
            "technician": _technician_payload(technician),
            "telegram_registration": latest_telegram_registration_payload(technician),
            "upcoming_calendar_events": [
                _calendar_event_payload(event)
                for event in CalendarEvent.objects.select_related("technician")
                .filter(technician=technician, start_at__gte=now, start_at__lt=end)
                .order_by("start_at")[:20]
            ],
            "latest_work_reports": [
                _work_report_payload(report, include_money=include_money)
                for report in WorkReport.objects.filter(technician=technician).order_by("-created_at")[:10]
            ],
        }

        if include_money:
            data["latest_expenses"] = [
                _expense_payload(expense)
                for expense in ExpenseReport.objects.filter(technician=technician).order_by("-created_at")[:10]
            ]
            data["latest_contracts"] = [
                _contract_payload(contract)
                for contract in ServiceContract.objects.filter(technician=technician).order_by("-created_at")[:10]
            ]

        return Response(data)


class ScheduleView(APIView):
    permission_classes = [DashboardPermission]
    dashboard_endpoint = "schedule"

    def get(self, request):
        today = timezone.localdate()
        start_date = _parse_date_param(request.query_params, "start_date", today)
        end_date = _parse_date_param(request.query_params, "end_date", today + timedelta(days=7))
        if start_date > end_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

        queryset = CalendarEvent.objects.select_related("technician").filter(
            start_at__date__gte=start_date,
            start_at__date__lte=end_date,
        )
        technician = request.query_params.get("technician")
        if technician:
            queryset = queryset.filter(technician_id=technician)

        return Response(
            {
                "start_date": start_date,
                "end_date": end_date,
                "events": [_calendar_event_payload(event) for event in queryset.order_by("start_at", "technician_id")],
            }
        )


class FinanceSummaryView(APIView):
    permission_classes = [DashboardPermission]
    dashboard_endpoint = "finance_summary"

    def get(self, request):
        start_date = _parse_date_param(request.query_params, "start_date")
        end_date = _parse_date_param(request.query_params, "end_date")
        if start_date is None or end_date is None:
            raise ValidationError({"date_range": "start_date and end_date are required."})
        if start_date > end_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

        technician = request.query_params.get("technician")
        reports = WorkReport.objects.filter(report_date__gte=start_date, report_date__lte=end_date)
        expenses = ExpenseReport.objects.filter(expense_date__gte=start_date, expense_date__lte=end_date)
        if technician:
            reports = reports.filter(technician_id=technician)
            expenses = expenses.filter(technician_id=technician)

        if technician:
            revenue = reports.aggregate(total=Sum("amount"))["total"] or ZERO
            expenses_total = expenses.aggregate(total=Sum("amount"))["total"] or ZERO
            return Response(
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "technician": int(technician),
                    "total_revenue": _money(revenue),
                    "total_expenses": _money(expenses_total),
                    "net": _money(revenue - expenses_total),
                    "reports_count": reports.count(),
                    "expenses_count": expenses.count(),
                }
            )

        report_rows = {
            row["technician_id"]: row
            for row in reports.values("technician_id", "technician__display_name", "technician__first_name", "technician__last_name")
            .annotate(total_revenue=Coalesce(Sum("amount"), ZERO_VALUE), reports_count=Count("id"))
            .order_by("technician__last_name", "technician__first_name")
        }
        expense_rows = {
            row["technician_id"]: row
            for row in expenses.values("technician_id")
            .annotate(total_expenses=Coalesce(Sum("amount"), ZERO_VALUE), expenses_count=Count("id"))
        }
        technician_ids = sorted(set(report_rows) | set(expense_rows))

        groups = []
        total_revenue = ZERO
        total_expenses = ZERO
        total_reports_count = 0
        total_expenses_count = 0
        technician_names = {
            technician.id: str(technician)
            for technician in Technician.objects.filter(id__in=technician_ids)
        }
        for technician_id in technician_ids:
            report_row = report_rows.get(technician_id, {})
            expense_row = expense_rows.get(technician_id, {})
            revenue = report_row.get("total_revenue") or ZERO
            expenses_value = expense_row.get("total_expenses") or ZERO
            reports_count = report_row.get("reports_count", 0)
            expenses_count = expense_row.get("expenses_count", 0)
            total_revenue += revenue
            total_expenses += expenses_value
            total_reports_count += reports_count
            total_expenses_count += expenses_count
            groups.append(
                {
                    "technician": technician_id,
                    "technician_display_name": technician_names.get(technician_id, ""),
                    "total_revenue": _money(revenue),
                    "total_expenses": _money(expenses_value),
                    "net": _money(revenue - expenses_value),
                    "reports_count": reports_count,
                    "expenses_count": expenses_count,
                }
            )

        return Response(
            {
                "start_date": start_date,
                "end_date": end_date,
                "total_revenue": _money(total_revenue),
                "total_expenses": _money(total_expenses),
                "net": _money(total_revenue - total_expenses),
                "reports_count": total_reports_count,
                "expenses_count": total_expenses_count,
                "by_technician": groups,
            }
        )
