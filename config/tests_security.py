from datetime import date, datetime, time
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserRole
from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from contracts.models import CleaningProjectType, ServiceContract
from expenses.models import ExpenseReport, ExpenseType
from reports.models import ClosedBy, PaymentType, ReviewStatus, WorkReport
from technicians.models import Technician, TechnicianStatus


ROLE_ORDER = [
    UserRole.OWNER,
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.DISPATCHER,
    UserRole.CALL_CENTER,
    UserRole.ACCOUNTANT,
    UserRole.TECHNICIAN,
    "anonymous",
]


@override_settings(DEBUG=False, TECHNICIAN_BOT_TOKEN="bot-token")
class ApiEndpointRoleSecurityTests(TestCase):
    def setUp(self):
        self.users = {}
        for role in ROLE_ORDER[:-1]:
            user = User.objects.create_user(username=role.lower(), password="password")
            user.profile.role = role
            if role in {UserRole.OWNER, UserRole.ADMIN}:
                user.is_staff = True
                user.save(update_fields=["is_staff"])
            user.profile.save(update_fields=["role", "updated_at"])
            self.users[role] = user

        self.technician = Technician.objects.create(
            first_name="Secure",
            last_name="Tech",
            display_name="Secure Tech",
            status=TechnicianStatus.ONBOARDING,
            telegram_user_id="123456789",
            telegram_group_chat_id="-1001234567890",
            google_calendar_id="secure-tech@example.com",
        )
        self.calendar_event = CalendarEvent.objects.create(
            technician=self.technician,
            google_calendar_id=self.technician.google_calendar_id,
            google_event_id="evt-1",
            event_type=CalendarEventType.JOB,
            status=CalendarEventStatus.SCHEDULED,
            title="1. Security Check",
            location="123 Main St",
            description="Scheduled service visit",
            start_at=timezone.make_aware(datetime.combine(date(2026, 5, 2), time(9, 0))),
            end_at=timezone.make_aware(datetime.combine(date(2026, 5, 2), time(11, 0))),
            timezone="America/Los_Angeles",
            job_number="1001",
        )
        self.work_report = WorkReport.objects.create(
            technician=self.technician,
            calendar_event=self.calendar_event,
            report_date=date(2026, 5, 2),
            job_number="1001",
            payment_type=PaymentType.CASH,
            amount=Decimal("125.00"),
            closed_by=ClosedBy.TECHNICIAN,
            google_review=ReviewStatus.YES,
            groupon_review=ReviewStatus.NO,
            yearly_maintenance_plan=ReviewStatus.YES,
        )
        self.expense_report = ExpenseReport.objects.create(
            technician=self.technician,
            calendar_event=self.calendar_event,
            expense_date=date(2026, 5, 2),
            expense_type=ExpenseType.GAS,
            amount=Decimal("15.50"),
        )
        self.service_contract = ServiceContract.objects.create(
            technician=self.technician,
            calendar_event=self.calendar_event,
            contract_date=date(2026, 5, 2),
            customer_name="Customer Name",
            customer_address="123 Main St",
            customer_phone="555-1111",
            project_type=CleaningProjectType.AIR_DUCT_CLEANING,
            subtotal=Decimal("100.00"),
            sales_tax=Decimal("8.25"),
        )
        self._sequence = 0

    def test_role_security_matrix_for_api_endpoints(self):
        cases = [
            {
                "name": "health_get",
                "method": "get",
                "url": "/api/health/",
                "allowed_roles": set(ROLE_ORDER),
                "allowed_statuses": {200},
            },
            {
                "name": "auth_login_post",
                "method": "post",
                "url": "/api/auth/login/",
                "allowed_roles": set(ROLE_ORDER),
                "allowed_statuses": {401},
                "data_factory": lambda: {"username": "missing", "password": "wrong"},
            },
            {
                "name": "auth_refresh_post",
                "method": "post",
                "url": "/api/auth/refresh/",
                "allowed_roles": set(ROLE_ORDER),
                "allowed_statuses": {400, 401},
                "data_factory": lambda: {"refresh": "invalid"},
            },
            {
                "name": "auth_me_get",
                "method": "get",
                "url": "/api/auth/me/",
                "allowed_roles": set(ROLE_ORDER[:-1]),
                "allowed_statuses": {200},
            },
            {
                "name": "accounts_profiles_get",
                "method": "get",
                "url": "/api/accounts/profiles/",
                "allowed_roles": {UserRole.OWNER, UserRole.ADMIN},
                "allowed_statuses": {200},
            },
            {
                "name": "calendar_events_get",
                "method": "get",
                "url": "/api/calendar/events/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "calendar_events_post",
                "method": "post",
                "url": "/api/calendar/events/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {201},
                "data_factory": self._calendar_event_payload,
            },
            {
                "name": "calendar_sync_post",
                "method": "post",
                "url": "/api/calendar/sync-technician/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {200},
                "data_factory": lambda: {"technician_id": self.technician.id, "days_ahead": 14},
                "patch_target": "calendar_sync.views.sync_google_calendar_for_technician",
                "patch_return": {"technician_id": 1, "created": 1, "updated": 0, "skipped": 0},
            },
            {
                "name": "calendar_send_schedule_post",
                "method": "post",
                "url": "/api/calendar/send-technician-schedule/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {200},
                "data_factory": lambda: {"technician_id": self.technician.id, "date": "2026-05-04"},
                "patch_target": "calendar_sync.views.send_technician_schedule",
                "patch_return": {
                    "technician_id": self.technician.id,
                    "target_date": "2026-05-04",
                    "sent": True,
                    "events_count": 1,
                    "error": "",
                },
            },
            {
                "name": "contracts_get",
                "method": "get",
                "url": "/api/contracts/service-contracts/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                    UserRole.ACCOUNTANT,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "contracts_post",
                "method": "post",
                "url": "/api/contracts/service-contracts/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {201},
                "data_factory": self._contract_payload,
                "patch_target": "contracts.views.ContractSubmissionService.submit_contract",
                "patch_return": None,
            },
            {
                "name": "dashboard_overview_get",
                "method": "get",
                "url": "/api/dashboard/overview/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "dashboard_technician_detail_get",
                "method": "get",
                "url": f"/api/dashboard/technicians/{self.technician.id}/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "dashboard_schedule_get",
                "method": "get",
                "url": "/api/dashboard/schedule/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "dashboard_finance_get",
                "method": "get",
                "url": "/api/dashboard/finance-summary/?start_date=2026-05-01&end_date=2026-05-03",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.ACCOUNTANT,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "expenses_get",
                "method": "get",
                "url": "/api/expenses/expense-reports/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.ACCOUNTANT,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "expenses_post",
                "method": "post",
                "url": "/api/expenses/expense-reports/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                },
                "allowed_statuses": {201},
                "data_factory": self._expense_payload,
                "patch_target": "expenses.views.ExpenseSubmissionService.submit_expense",
                "patch_return": None,
            },
            {
                "name": "reports_get",
                "method": "get",
                "url": "/api/reports/work-reports/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                    UserRole.ACCOUNTANT,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "reports_post",
                "method": "post",
                "url": "/api/reports/work-reports/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                },
                "allowed_statuses": {201},
                "data_factory": self._work_report_payload,
                "patch_target": "reports.views.ReportSubmissionService.submit_report",
                "patch_return": None,
            },
            {
                "name": "reports_daily_summary_get",
                "method": "get",
                "url": "/api/reports/daily-summary/?date=2026-05-02",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.ACCOUNTANT,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "reports_weekly_summary_get",
                "method": "get",
                "url": "/api/reports/weekly-summary/?week_start=2026-04-27",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.ACCOUNTANT,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "submit_work_report_post",
                "method": "post",
                "url": "/api/technician/submit-work-report/",
                "allowed_roles": set(),
                "allowed_statuses": set(),
                "data_factory": lambda: {
                    "telegram_user_id": "123456789",
                    "report_date": "2026-05-02",
                    "payment_type": "CASH",
                    "amount": "100.00",
                    "closed_by": "TECHNICIAN",
                    "groupon_review": "NO",
                    "google_review": "NO",
                    "yearly_maintenance_plan": "NO",
                },
            },
            {
                "name": "submit_expense_post",
                "method": "post",
                "url": "/api/technician/submit-expense/",
                "allowed_roles": set(),
                "allowed_statuses": set(),
                "data_factory": lambda: {
                    "telegram_user_id": "123456789",
                    "expense_date": "2026-05-02",
                    "expense_type": "GAS",
                    "amount": "10.00",
                },
            },
            {
                "name": "submit_contract_post",
                "method": "post",
                "url": "/api/technician/submit-contract/",
                "allowed_roles": set(),
                "allowed_statuses": set(),
                "data_factory": lambda: {
                    "telegram_user_id": "123456789",
                    "contract_date": "2026-05-02",
                    "customer_name": "Customer",
                    "customer_address": "123 Main St",
                    "customer_phone": "555-1111",
                    "project_type": "AIR_DUCT_CLEANING",
                    "subtotal": "100.00",
                    "sales_tax": "8.25",
                },
            },
            {
                "name": "technicians_get",
                "method": "get",
                "url": "/api/technicians/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                    UserRole.DISPATCHER,
                    UserRole.CALL_CENTER,
                    UserRole.ACCOUNTANT,
                },
                "allowed_statuses": {200},
            },
            {
                "name": "technicians_post",
                "method": "post",
                "url": "/api/technicians/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                },
                "allowed_statuses": {201},
                "data_factory": self._technician_payload,
            },
            {
                "name": "technicians_activate_post",
                "method": "post",
                "url": f"/api/technicians/{self.technician.id}/activate/",
                "allowed_roles": {
                    UserRole.OWNER,
                    UserRole.ADMIN,
                    UserRole.MANAGER,
                },
                "allowed_statuses": {200},
                "data_factory": lambda: {},
            },
        ]

        for case in cases:
            for role in ROLE_ORDER:
                with self.subTest(endpoint=case["name"], role=role):
                    response = self._request_for_case(case, role)
                    if role in case["allowed_roles"]:
                        self.assertIn(response.status_code, case["allowed_statuses"])
                    else:
                        self.assertIn(response.status_code, {401, 403})

    def _request_for_case(self, case, role):
        client = APIClient()
        if role != "anonymous":
            client.force_authenticate(user=self.users[role])

        data = case.get("data_factory", lambda: None)()
        patch_target = case.get("patch_target")
        patch_return = case.get("patch_return")
        if case["name"] == "contracts_post" and patch_return is None:
            patch_return = self.service_contract
        if case["name"] == "expenses_post" and patch_return is None:
            patch_return = self.expense_report
        if case["name"] == "reports_post" and patch_return is None:
            patch_return = self.work_report

        if patch_target:
            with mock.patch(patch_target, return_value=patch_return):
                return getattr(client, case["method"])(case["url"], data, format="json")
        return getattr(client, case["method"])(case["url"], data, format="json")

    def _technician_payload(self):
        self._sequence += 1
        return {
            "first_name": f"Tech{self._sequence}",
            "last_name": "Created",
            "display_name": f"Created Tech {self._sequence}",
            "phone": "555-0100",
            "email": f"created{self._sequence}@example.com",
            "status": TechnicianStatus.ONBOARDING,
            "service_state": "CA",
            "timezone": "America/Los_Angeles",
            "telegram_user_id": str(900000000 + self._sequence),
            "telegram_username": f"tech_{self._sequence}",
            "telegram_group_chat_id": str(-1009000000000 - self._sequence),
            "google_calendar_id": f"created-{self._sequence}@example.com",
            "notes": "Created during security test.",
        }

    def _calendar_event_payload(self):
        self._sequence += 1
        return {
            "technician": self.technician.id,
            "google_calendar_id": self.technician.google_calendar_id,
            "google_event_id": f"evt-created-{self._sequence}",
            "event_type": CalendarEventType.JOB,
            "status": CalendarEventStatus.SCHEDULED,
            "title": f"{1000 + self._sequence}. New Event",
            "location": "500 Test Ave",
            "description": "Created during security test.",
            "start_at": "2026-05-03T09:00:00-07:00",
            "end_at": "2026-05-03T11:00:00-07:00",
            "timezone": "America/Los_Angeles",
            "job_number": f"{1000 + self._sequence}",
            "is_report_required": True,
            "raw_google_payload": {},
        }

    def _work_report_payload(self):
        return {
            "technician": self.technician.id,
            "calendar_event": self.calendar_event.id,
            "report_date": "2026-05-02",
            "job_number": "1001",
            "payment_type": PaymentType.CASH,
            "amount": "100.00",
            "closed_by": ClosedBy.TECHNICIAN,
            "groupon_review": ReviewStatus.NO,
            "google_review": ReviewStatus.YES,
            "yearly_maintenance_plan": ReviewStatus.NO,
        }

    def _expense_payload(self):
        return {
            "technician": self.technician.id,
            "calendar_event": self.calendar_event.id,
            "expense_date": "2026-05-02",
            "expense_type": ExpenseType.GAS,
            "amount": "25.00",
            "description": "Gas refill",
            "receipt_photo_url": "https://example.com/receipt.jpg",
        }

    def _contract_payload(self):
        return {
            "technician": self.technician.id,
            "calendar_event": self.calendar_event.id,
            "contract_date": "2026-05-02",
            "customer_name": "Customer Name",
            "customer_address": "123 Main St",
            "customer_phone": "555-1111",
            "project_type": CleaningProjectType.AIR_DUCT_CLEANING,
            "subtotal": "100.00",
            "sales_tax": "8.25",
        }


class ValidationHardeningTests(TestCase):
    def setUp(self):
        self.technician = Technician.objects.create(
            first_name="Validation",
            last_name="Tech",
            display_name="Validation Tech",
            telegram_user_id="333444555",
            telegram_group_chat_id="-100333444555",
            google_calendar_id="validation@example.com",
        )
        self.calendar_event = CalendarEvent.objects.create(
            technician=self.technician,
            google_calendar_id=self.technician.google_calendar_id,
            google_event_id="evt-validation",
            event_type=CalendarEventType.JOB,
            status=CalendarEventStatus.SCHEDULED,
            title="1. Validation Visit",
            location="123 Main St",
            description="Validation event",
            start_at=timezone.make_aware(datetime.combine(date(2026, 5, 2), time(9, 0))),
            end_at=timezone.make_aware(datetime.combine(date(2026, 5, 2), time(11, 0))),
            timezone="America/Los_Angeles",
            job_number="1001",
        )
        self.user = User.objects.create_user(username="manager", password="password")
        self.user.profile.role = UserRole.MANAGER
        self.user.profile.save(update_fields=["role", "updated_at"])
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_technician_serializer_rejects_non_numeric_telegram_ids(self):
        response = self.client.post(
            "/api/technicians/",
            {
                "first_name": "Bad",
                "last_name": "Ids",
                "status": TechnicianStatus.ONBOARDING,
                "timezone": "America/Los_Angeles",
                "telegram_user_id": "abc123",
                "telegram_group_chat_id": "group-chat",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("telegram_user_id", response.json())
        self.assertIn("telegram_group_chat_id", response.json())

    def test_reports_api_rejects_negative_amounts(self):
        response = self.client.post(
            "/api/reports/work-reports/",
            {
                "technician": self.technician.id,
                "calendar_event": self.calendar_event.id,
                "report_date": "2026-05-02",
                "payment_type": PaymentType.CASH,
                "amount": "-1.00",
                "closed_by": ClosedBy.TECHNICIAN,
                "groupon_review": ReviewStatus.NO,
                "google_review": ReviewStatus.NO,
                "yearly_maintenance_plan": ReviewStatus.NO,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.json())

    def test_expenses_api_rejects_negative_amounts_and_non_http_receipt_url(self):
        response = self.client.post(
            "/api/expenses/expense-reports/",
            {
                "technician": self.technician.id,
                "calendar_event": self.calendar_event.id,
                "expense_date": "2026-05-02",
                "expense_type": ExpenseType.GAS,
                "amount": "-4.00",
                "description": "Fuel",
                "receipt_photo_url": "ftp://example.com/receipt.jpg",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.json())

    def test_expenses_api_rejects_non_http_receipt_url(self):
        response = self.client.post(
            "/api/expenses/expense-reports/",
            {
                "technician": self.technician.id,
                "calendar_event": self.calendar_event.id,
                "expense_date": "2026-05-02",
                "expense_type": ExpenseType.GAS,
                "amount": "4.00",
                "description": "Fuel",
                "receipt_photo_url": "ftp://example.com/receipt.jpg",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("receipt_photo_url", response.json())

    def test_contracts_api_rejects_negative_amounts(self):
        response = self.client.post(
            "/api/contracts/service-contracts/",
            {
                "technician": self.technician.id,
                "calendar_event": self.calendar_event.id,
                "contract_date": "2026-05-02",
                "customer_name": "Customer",
                "customer_address": "123 Main St",
                "customer_phone": "555-1111",
                "project_type": CleaningProjectType.AIR_DUCT_CLEANING,
                "subtotal": "-10.00",
                "sales_tax": "8.25",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("subtotal", response.json())

    @override_settings(DEBUG=True, TECHNICIAN_API_SHARED_SECRET="shared-secret")
    def test_submission_validators_limit_comment_and_description_lengths(self):
        too_long = "x" * 2001
        response = self.client.post(
            "/api/technician/submit-work-report/",
            {
                "telegram_user_id": self.technician.telegram_user_id,
                "report_date": "2026-05-02",
                "payment_type": PaymentType.CASH,
                "amount": "10.00",
                "closed_by": ClosedBy.TECHNICIAN,
                "project_description": too_long,
                "comments": too_long,
                "groupon_review": ReviewStatus.NO,
                "google_review": ReviewStatus.NO,
                "yearly_maintenance_plan": ReviewStatus.NO,
            },
            format="json",
            HTTP_X_TECHNICIAN_API_SECRET="shared-secret",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("project_description", response.json())
        self.assertIn("comments", response.json())

    def test_expenses_and_contracts_limit_description_lengths(self):
        too_long = "x" * 2001

        expense_response = self.client.post(
            "/api/expenses/expense-reports/",
            {
                "technician": self.technician.id,
                "calendar_event": self.calendar_event.id,
                "expense_date": "2026-05-02",
                "expense_type": ExpenseType.GAS,
                "amount": "4.00",
                "description": too_long,
                "receipt_photo_url": "https://example.com/receipt.jpg",
            },
            format="json",
        )
        contract_response = self.client.post(
            "/api/contracts/service-contracts/",
            {
                "technician": self.technician.id,
                "calendar_event": self.calendar_event.id,
                "contract_date": "2026-05-02",
                "customer_name": "Customer",
                "customer_address": "123 Main St",
                "customer_phone": "555-1111",
                "project_type": CleaningProjectType.AIR_DUCT_CLEANING,
                "project_description": too_long,
                "subtotal": "100.00",
                "sales_tax": "8.25",
            },
            format="json",
        )

        self.assertEqual(expense_response.status_code, 400)
        self.assertIn("description", expense_response.json())
        self.assertEqual(contract_response.status_code, 400)
        self.assertIn("project_description", contract_response.json())


class DeploySecurityCheckTests(TestCase):
    @override_settings(
        DEBUG=False,
        DJANGO_SECRET_KEY="test-secret",
        ALLOWED_HOSTS=["example.com"],
        CSRF_TRUSTED_ORIGINS=["https://example.com"],
        CORS_ALLOWED_ORIGINS=["https://frontend.example.com"],
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=31536000,
    )
    def test_production_like_settings_are_present(self):
        from django.conf import settings

        self.assertTrue(settings.SECURE_SSL_REDIRECT)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 31536000)
