from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserRole
from expenses.models import ExpenseReport, ExpenseType
from reports.models import ClosedBy, PaymentType, ReviewStatus, WorkReport
from technicians.models import Technician


class WorkReportModelTests(TestCase):
    def setUp(self):
        self.technician = Technician.objects.create(
            first_name="Model",
            last_name="Tech",
            display_name="Model Tech",
        )

    def test_estimate_and_cancel_amounts_normalize_to_zero(self):
        estimate = WorkReport.objects.create(
            technician=self.technician,
            report_date=date(2026, 5, 2),
            payment_type=PaymentType.ESTIMATE,
            amount=Decimal("999.99"),
            closed_by=ClosedBy.TECHNICIAN,
        )
        cancel = WorkReport.objects.create(
            technician=self.technician,
            report_date=date(2026, 5, 2),
            payment_type=PaymentType.CANCEL,
            amount=Decimal("555.55"),
            closed_by=ClosedBy.CUSTOMER,
        )

        self.assertEqual(estimate.amount, Decimal("0.00"))
        self.assertEqual(cancel.amount, Decimal("0.00"))


class ReportSummaryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user(username="manager", password="password")
        self.manager.profile.role = UserRole.MANAGER
        self.manager.profile.save(update_fields=["role", "updated_at"])
        self.call_center = User.objects.create_user(username="callcenter", password="password")
        self.call_center.profile.role = UserRole.CALL_CENTER
        self.call_center.profile.save(update_fields=["role", "updated_at"])

        self.tech_one = Technician.objects.create(
            first_name="Summary",
            last_name="One",
            display_name="Summary One",
        )
        self.tech_two = Technician.objects.create(
            first_name="Summary",
            last_name="Two",
            display_name="Summary Two",
        )

        WorkReport.objects.create(
            technician=self.tech_one,
            report_date=date(2026, 5, 2),
            job_number="1001",
            address="123 Alpha St",
            payment_type=PaymentType.CASH,
            amount=Decimal("100.00"),
            closed_by=ClosedBy.TECHNICIAN,
            google_review=ReviewStatus.YES,
            groupon_review=ReviewStatus.NO,
            yearly_maintenance_plan=ReviewStatus.YES,
        )
        WorkReport.objects.create(
            technician=self.tech_one,
            report_date=date(2026, 5, 2),
            job_number="1002",
            address="123 Beta St",
            payment_type=PaymentType.ESTIMATE,
            amount=Decimal("999.99"),
            closed_by=ClosedBy.TECHNICIAN,
            google_review=ReviewStatus.NO,
            groupon_review=ReviewStatus.YES,
            yearly_maintenance_plan=ReviewStatus.NO,
        )
        WorkReport.objects.create(
            technician=self.tech_two,
            report_date=date(2026, 5, 2),
            job_number="1003",
            address="123 Gamma St",
            payment_type=PaymentType.CREDIT_CARD,
            amount=Decimal("200.00"),
            closed_by=ClosedBy.MANAGER,
            google_review=ReviewStatus.YES,
            groupon_review=ReviewStatus.YES,
            yearly_maintenance_plan=ReviewStatus.NO,
        )
        WorkReport.objects.create(
            technician=self.tech_two,
            report_date=date(2026, 4, 27),
            job_number="0999",
            address="123 Delta St",
            payment_type=PaymentType.CANCEL,
            amount=Decimal("500.00"),
            closed_by=ClosedBy.CUSTOMER,
        )

        ExpenseReport.objects.create(
            technician=self.tech_one,
            expense_date=date(2026, 5, 2),
            expense_type=ExpenseType.GAS,
            amount=Decimal("25.50"),
        )
        ExpenseReport.objects.create(
            technician=self.tech_two,
            expense_date=date(2026, 5, 2),
            expense_type=ExpenseType.PARTS,
            amount=Decimal("40.00"),
        )
        ExpenseReport.objects.create(
            technician=self.tech_two,
            expense_date=date(2026, 4, 27),
            expense_type=ExpenseType.PARKING,
            amount=Decimal("10.00"),
        )

    def test_daily_summary_totals(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/reports/daily-summary/?date=2026-05-02")

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["reports_count"], 3)
        self.assertEqual(data["total_revenue"], "300.00")
        self.assertEqual(data["expenses_total"], "65.50")
        self.assertEqual(data["net_total"], "234.50")
        self.assertEqual(data["reviews"]["google_review_yes"], 2)
        self.assertEqual(data["reviews"]["groupon_review_yes"], 2)
        self.assertEqual(data["reviews"]["yearly_maintenance_plan_yes"], 1)
        self.assertEqual(len(data["reports"]), 3)

    def test_weekly_summary_totals(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/reports/weekly-summary/?week_start=2026-04-27")

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["reports_count"], 4)
        self.assertEqual(data["total_revenue"], "300.00")
        self.assertEqual(data["expenses_total"], "75.50")
        self.assertEqual(data["net_total"], "224.50")
        self.assertEqual(len(data["by_day"]), 7)
        self.assertEqual(len(data["by_technician"]), 2)

    def test_call_center_is_denied_summary_access(self):
        self.client.force_authenticate(user=self.call_center)

        response = self.client.get("/api/reports/daily-summary/?date=2026-05-02")

        self.assertEqual(response.status_code, 403)
