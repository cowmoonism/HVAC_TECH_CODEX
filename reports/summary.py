from decimal import Decimal

from django.db.models import Sum

from expenses.models import ExpenseReport
from reports.models import PaymentType, ReviewStatus, WorkReport
from technicians.models import Technician


ZERO = Decimal("0.00")


def build_daily_summary(target_date, technician_id=None):
    reports = WorkReport.objects.select_related("technician", "calendar_event").filter(report_date=target_date)
    expenses = ExpenseReport.objects.select_related("technician", "calendar_event").filter(expense_date=target_date)
    if technician_id:
        reports = reports.filter(technician_id=technician_id)
        expenses = expenses.filter(technician_id=technician_id)

    total_revenue = reports.aggregate(total=Sum("amount"))["total"] or ZERO
    expenses_total = expenses.aggregate(total=Sum("amount"))["total"] or ZERO

    return {
        "date": str(target_date),
        "technician": int(technician_id) if technician_id else None,
        "reports_count": reports.count(),
        "total_revenue": _money(total_revenue),
        "expenses_total": _money(expenses_total),
        "net_total": _money(total_revenue - expenses_total),
        "by_payment_type": _payment_type_summary(reports),
        "reviews": _reviews_summary(reports),
        "reports": [_daily_report_payload(report) for report in reports.order_by("-created_at")],
    }


def build_weekly_summary(week_start, technician_id=None):
    week_end = week_start + _one_week_minus_one_day()
    reports = WorkReport.objects.select_related("technician", "calendar_event").filter(
        report_date__gte=week_start,
        report_date__lte=week_end,
    )
    expenses = ExpenseReport.objects.select_related("technician", "calendar_event").filter(
        expense_date__gte=week_start,
        expense_date__lte=week_end,
    )
    if technician_id:
        reports = reports.filter(technician_id=technician_id)
        expenses = expenses.filter(technician_id=technician_id)

    total_revenue = reports.aggregate(total=Sum("amount"))["total"] or ZERO
    expenses_total = expenses.aggregate(total=Sum("amount"))["total"] or ZERO

    summary = {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "technician": int(technician_id) if technician_id else None,
        "reports_count": reports.count(),
        "total_revenue": _money(total_revenue),
        "expenses_total": _money(expenses_total),
        "net_total": _money(total_revenue - expenses_total),
        "by_day": _by_day_summary(week_start, week_end, reports, expenses),
        "by_payment_type": _payment_type_summary(reports),
        "reviews": _reviews_summary(reports),
    }
    if not technician_id:
        summary["by_technician"] = _by_technician_summary(reports, expenses)
    return summary


def _daily_report_payload(report):
    return {
        "id": report.id,
        "technician": report.technician_id,
        "technician_display_name": str(report.technician),
        "report_date": str(report.report_date),
        "job_number": report.job_number,
        "address": report.address,
        "payment_type": report.payment_type,
        "amount": _money(report.amount),
        "closed_by": report.closed_by,
        "google_review": report.google_review,
        "groupon_review": report.groupon_review,
        "yearly_maintenance_plan": report.yearly_maintenance_plan,
    }


def _payment_type_summary(reports):
    result = []
    for payment_type, _label in PaymentType.choices:
        payment_reports = reports.filter(payment_type=payment_type)
        count = payment_reports.count()
        if not count:
            continue
        total = payment_reports.aggregate(total=Sum("amount"))["total"] or ZERO
        result.append(
            {
                "payment_type": payment_type,
                "reports_count": count,
                "total_revenue": _money(total),
            }
        )
    return result


def _reviews_summary(reports):
    return {
        "google_review_yes": reports.filter(google_review=ReviewStatus.YES).count(),
        "groupon_review_yes": reports.filter(groupon_review=ReviewStatus.YES).count(),
        "yearly_maintenance_plan_yes": reports.filter(yearly_maintenance_plan=ReviewStatus.YES).count(),
    }


def _by_day_summary(week_start, week_end, reports, expenses):
    result = []
    current_day = week_start
    while current_day <= week_end:
        day_reports = reports.filter(report_date=current_day)
        day_expenses = expenses.filter(expense_date=current_day)
        day_revenue = day_reports.aggregate(total=Sum("amount"))["total"] or ZERO
        day_expenses_total = day_expenses.aggregate(total=Sum("amount"))["total"] or ZERO
        result.append(
            {
                "date": str(current_day),
                "reports_count": day_reports.count(),
                "total_revenue": _money(day_revenue),
                "expenses_total": _money(day_expenses_total),
                "net_total": _money(day_revenue - day_expenses_total),
            }
        )
        current_day += _one_day()
    return result


def _by_technician_summary(reports, expenses):
    technician_ids = sorted(set(reports.values_list("technician_id", flat=True)) | set(expenses.values_list("technician_id", flat=True)))
    technicians = {technician.id: str(technician) for technician in Technician.objects.filter(id__in=technician_ids)}
    result = []
    for technician_id in technician_ids:
        tech_reports = reports.filter(technician_id=technician_id)
        tech_expenses = expenses.filter(technician_id=technician_id)
        revenue = tech_reports.aggregate(total=Sum("amount"))["total"] or ZERO
        expenses_total = tech_expenses.aggregate(total=Sum("amount"))["total"] or ZERO
        result.append(
            {
                "technician": technician_id,
                "technician_display_name": technicians.get(technician_id, ""),
                "reports_count": tech_reports.count(),
                "total_revenue": _money(revenue),
                "expenses_total": _money(expenses_total),
                "net_total": _money(revenue - expenses_total),
            }
        )
    return result


def _money(value):
    return f"{value or ZERO:.2f}"


def _one_day():
    from datetime import timedelta

    return timedelta(days=1)


def _one_week_minus_one_day():
    from datetime import timedelta

    return timedelta(days=6)
