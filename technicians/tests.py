import hashlib
import hmac
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserRole
from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from contracts.models import ServiceContract
from reports.models import WorkReport
from technicians.form_tokens import create_technician_form_token
from technicians.models import (
    Technician,
    TechnicianStatus,
    TechnicianTelegramRegistration,
    TechnicianTelegramRegistrationStatus,
)


class TechnicianActivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager", password="password")
        self.user.profile.role = UserRole.MANAGER
        self.user.profile.save(update_fields=["role", "updated_at"])
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_activate_requires_integration_fields(self):
        technician = Technician.objects.create(
            first_name="Test",
            last_name="Tech",
            display_name="Test Tech",
            status=TechnicianStatus.ONBOARDING,
        )

        response = self.client.post(f"/api/technicians/{technician.id}/activate/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["missing_fields"],
            ["telegram_user_id", "telegram_group_chat_id", "google_calendar_id"],
        )

    def test_activate_succeeds_when_required_fields_exist(self):
        technician = Technician.objects.create(
            first_name="Ready",
            last_name="Tech",
            display_name="Ready Tech",
            status=TechnicianStatus.ONBOARDING,
            telegram_user_id="tg-user-1",
            telegram_group_chat_id="-100123",
            google_calendar_id="calendar@example.com",
        )

        response = self.client.post(f"/api/technicians/{technician.id}/activate/", {}, format="json")

        technician.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(technician.status, TechnicianStatus.ACTIVE)


class TechnicianSubmissionAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.technician = Technician.objects.create(
            first_name="Submit",
            last_name="Tech",
            display_name="Submit Tech",
            telegram_user_id="12345",
            telegram_group_chat_id="-10012345",
        )
        self.payload = {
            "telegram_user_id": "12345",
            "report_date": "2026-05-02",
            "job_number": "SUB-1",
            "payment_type": "CASH",
            "amount": "100.00",
            "closed_by": "TECHNICIAN",
            "groupon_review": "NO",
            "google_review": "YES",
            "yearly_maintenance_plan": "NO",
        }

    @override_settings(DEBUG=False, TECHNICIAN_BOT_TOKEN="bot-token")
    def test_invalid_init_data_is_rejected(self):
        response = self.client.post(
            "/api/technician/submit-work-report/",
            self.payload,
            format="json",
            HTTP_X_TELEGRAM_WEBAPP_INITDATA="user=%7B%22id%22%3A12345%7D&hash=invalid",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("invalid", response.json()["detail"].lower())

    @override_settings(DEBUG=False, TECHNICIAN_BOT_TOKEN="bot-token")
    def test_old_init_data_is_rejected(self):
        init_data = self._build_init_data(
            bot_token="bot-token",
            user_id=12345,
            auth_date=int((timezone.now() - timedelta(minutes=11)).timestamp()),
        )

        response = self.client.post(
            "/api/technician/submit-work-report/",
            self.payload,
            format="json",
            HTTP_X_TELEGRAM_WEBAPP_INITDATA=init_data,
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("too old", response.json()["detail"].lower())

    @override_settings(DEBUG=False, TECHNICIAN_BOT_TOKEN="bot-token")
    def test_debug_false_ignores_body_telegram_user_id_when_init_data_present(self):
        other_technician = Technician.objects.create(
            first_name="Real",
            last_name="Technician",
            display_name="Real Technician",
            telegram_user_id="67890",
            telegram_group_chat_id="-10099999",
        )
        payload = {
            **self.payload,
            "telegram_user_id": "12345",
        }
        init_data = self._build_init_data(
            bot_token="bot-token",
            user_id=int(other_technician.telegram_user_id),
            auth_date=int(timezone.now().timestamp()),
        )

        response = self.client.post(
            "/api/technician/submit-work-report/",
            payload,
            format="json",
            HTTP_X_TELEGRAM_WEBAPP_INITDATA=init_data,
        )

        self.assertEqual(response.status_code, 201)
        work_report = WorkReport.objects.latest("id")
        self.assertEqual(work_report.technician_id, other_technician.id)

    @override_settings(DEBUG=True, TECHNICIAN_API_SHARED_SECRET="shared-secret")
    def test_debug_shared_secret_fallback_works(self):
        response = self.client.post(
            "/api/technician/submit-work-report/",
            self.payload,
            format="json",
            HTTP_X_TECHNICIAN_API_SECRET="shared-secret",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["technician"], self.technician.id)

    @override_settings(DEBUG=False, TECHNICIAN_API_SHARED_SECRET="shared-secret")
    def test_signed_form_token_works_without_init_data(self):
        token = create_technician_form_token(
            {
                "telegram_user_id": self.technician.telegram_user_id,
                "telegram_group_chat_id": self.technician.telegram_group_chat_id,
            },
            "shared-secret",
        )
        payload = {
            **self.payload,
            "telegram_user_id": "untrusted-body-value",
        }

        response = self.client.post(
            "/api/technician/submit-work-report/",
            payload,
            format="json",
            HTTP_X_TECHNICIAN_FORM_TOKEN=token,
        )

        self.assertEqual(response.status_code, 201)
        work_report = WorkReport.objects.latest("id")
        self.assertEqual(work_report.technician_id, self.technician.id)

    @override_settings(DEBUG=False, TECHNICIAN_API_SHARED_SECRET="shared-secret")
    def test_signed_form_token_can_list_todays_active_calendar_events(self):
        today_start = timezone.localtime().replace(hour=10, minute=0, second=0, microsecond=0)
        active_event = CalendarEvent.objects.create(
            technician=self.technician,
            google_calendar_id="calendar@example.com",
            google_event_id="google-active-1",
            event_type=CalendarEventType.JOB,
            status=CalendarEventStatus.SCHEDULED,
            title="1. Active Duct Cleaning",
            location="100 Test Ave",
            start_at=today_start,
            end_at=today_start + timedelta(hours=2),
            job_number="1",
        )
        CalendarEvent.objects.create(
            technician=self.technician,
            google_calendar_id="calendar@example.com",
            google_event_id="google-canceled-1",
            event_type=CalendarEventType.JOB,
            status=CalendarEventStatus.CANCELED,
            title="2. Cancel hidden",
            location="200 Test Ave",
            start_at=today_start + timedelta(hours=3),
            end_at=today_start + timedelta(hours=5),
            job_number="2",
        )
        CalendarEvent.objects.create(
            technician=self.technician,
            google_calendar_id="calendar@example.com",
            google_event_id="google-tomorrow-1",
            event_type=CalendarEventType.JOB,
            status=CalendarEventStatus.SCHEDULED,
            title="3. Tomorrow hidden",
            location="300 Test Ave",
            start_at=today_start + timedelta(days=1),
            end_at=today_start + timedelta(days=1, hours=2),
            job_number="3",
        )
        WorkReport.objects.create(
            technician=self.technician,
            calendar_event=active_event,
            report_date=timezone.localdate(),
            payment_type="CASH",
            amount="25.00",
            closed_by="TECHNICIAN",
            groupon_review="NO",
            google_review="NO",
            yearly_maintenance_plan="NO",
        )
        token = create_technician_form_token(
            {
                "telegram_user_id": self.technician.telegram_user_id,
                "telegram_group_chat_id": self.technician.telegram_group_chat_id,
            },
            "shared-secret",
        )

        response = self.client.get(
            "/api/technician/calendar-events/",
            HTTP_X_TECHNICIAN_FORM_TOKEN=token,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["target_date"], timezone.localdate().isoformat())
        self.assertEqual(data["events_count"], 1)
        events = data["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["google_event_id"], "google-active-1")
        self.assertEqual(events[0]["day_sequence"], 1)
        self.assertEqual(events[0]["location"], "100 Test Ave")
        self.assertEqual(events[0]["report_count"], 1)

    @override_settings(DEBUG=False, TECHNICIAN_API_SHARED_SECRET="shared-secret")
    def test_contract_submission_accepts_full_card_but_redacts_raw_submission(self):
        token = create_technician_form_token(
            {
                "telegram_user_id": self.technician.telegram_user_id,
                "telegram_group_chat_id": self.technician.telegram_group_chat_id,
            },
            "shared-secret",
        )

        response = self.client.post(
            "/api/technician/submit-contract/",
            {
                "contract_date": "2026-05-02",
                "customer_name": "Card Customer",
                "customer_address": "500 Contract Ave",
                "customer_phone": "555-2000",
                "project_type": "AIR_DUCT_CLEANING",
                "project_description": "Contract with full card fields.",
                "subtotal": "250.00",
                "sales_tax": "20.63",
                "payment_processing_type": "MANUALLY_ENTERED",
                "credit_card_number": "4111 1111 1111 1111",
                "card_exp_date": "12/27",
                "card_csc": "123",
                "billing_zip_code": "90001",
            },
            format="json",
            HTTP_X_TECHNICIAN_FORM_TOKEN=token,
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertNotIn("credit_card_number", payload)
        self.assertNotIn("card_csc", payload)
        contract = ServiceContract.objects.latest("id")
        self.assertEqual(contract.credit_card_last4, "1111")
        self.assertFalse(hasattr(contract, "credit_card_number"))
        self.assertFalse(hasattr(contract, "card_csc"))
        self.assertEqual(contract.raw_submission["credit_card_number"], "[REDACTED]")
        self.assertEqual(contract.raw_submission["card_csc"], "[REDACTED]")

    def _build_init_data(self, *, bot_token, user_id, auth_date):
        payload = {
            "auth_date": str(auth_date),
            "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
            "user": json.dumps({"id": user_id}, separators=(",", ":")),
        }
        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        payload["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        return "&".join(f"{key}={value}" for key, value in payload.items())


@override_settings(TECHNICIAN_API_SHARED_SECRET="bot-shared-secret", TECHNICIAN_BOT_USERNAME="wa_test_bot")
class TechnicianTelegramRegistrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager-2", password="password")
        self.user.profile.role = UserRole.MANAGER
        self.user.profile.save(update_fields=["role", "updated_at"])
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.technician = Technician.objects.create(
            first_name="Pending",
            last_name="Tech",
            display_name="Pending Tech",
            status=TechnicianStatus.ONBOARDING,
        )
        self.bot_client = APIClient()

    def test_manager_can_start_registration_and_bot_can_link_group(self):
        start_response = self.client.post(
            f"/api/technicians/{self.technician.id}/start-telegram-registration/",
            {},
            format="json",
        )

        self.assertEqual(start_response.status_code, 201)
        token = start_response.json()["token"]
        self.assertIn("https://t.me/wa_test_bot?start=", start_response.json()["bot_start_url"])

        claim_response = self.bot_client.post(
            "/api/technician-bot/claim-registration/",
            {
                "token": token,
                "telegram_user_id": "777001",
                "telegram_username": "pendingtech",
            },
            format="json",
            HTTP_X_TECHNICIAN_BOT_SECRET="bot-shared-secret",
        )
        self.assertEqual(claim_response.status_code, 200)

        complete_response = self.bot_client.post(
            "/api/technician-bot/complete-registration/",
            {
                "telegram_user_id": "777001",
                "telegram_username": "pendingtech",
                "telegram_group_chat_id": "-100777001",
                "telegram_group_title": "Pending Tech Work Chat",
                "telegram_chat_type": "supergroup",
            },
            format="json",
            HTTP_X_TECHNICIAN_BOT_SECRET="bot-shared-secret",
        )
        self.assertEqual(complete_response.status_code, 200)

        self.technician.refresh_from_db()
        self.assertEqual(self.technician.telegram_user_id, "777001")
        self.assertEqual(self.technician.telegram_group_chat_id, "-100777001")

        registration = TechnicianTelegramRegistration.objects.get(technician=self.technician)
        self.assertEqual(registration.status, TechnicianTelegramRegistrationStatus.LINKED)
        self.assertEqual(registration.telegram_group_title, "Pending Tech Work Chat")

    def test_group_registration_requires_prior_claim(self):
        response = self.bot_client.post(
            "/api/technician-bot/complete-registration/",
            {
                "telegram_user_id": "555001",
                "telegram_username": "orphantech",
                "telegram_group_chat_id": "-100555001",
                "telegram_group_title": "Orphan Tech Work Chat",
                "telegram_chat_type": "supergroup",
            },
            format="json",
            HTTP_X_TECHNICIAN_BOT_SECRET="bot-shared-secret",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("No claimed technician registration", response.json()["detail"])
