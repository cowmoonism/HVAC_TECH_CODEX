from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import UserRole
from technicians.models import Technician, TechnicianStatus


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
