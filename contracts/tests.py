from datetime import date
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from contracts.models import CleaningProjectType, ContractStatus, ServiceContract
from contracts.services import ContractSubmissionService, generate_contract_pdf
from technicians.models import Technician


class ServiceContractPdfTests(TestCase):
    def setUp(self):
        self.technician = Technician.objects.create(
            first_name="Contract",
            last_name="Tech",
            display_name="Contract Tech",
        )
        self.contract = ServiceContract.objects.create(
            technician=self.technician,
            contract_date=date(2026, 5, 2),
            customer_name="Customer Name",
            customer_address="123 Main St",
            customer_phone="555-1111",
            project_type=CleaningProjectType.AIR_DUCT_CLEANING,
            subtotal="100.00",
            sales_tax="8.25",
        )

    def test_generate_contract_pdf_writes_file_and_updates_model(self):
        media_root = settings.BASE_DIR / "test-media"
        shutil.rmtree(media_root, ignore_errors=True)
        self.addCleanup(lambda: shutil.rmtree(media_root, ignore_errors=True))

        class FakeHtml:
            def __init__(self, string, base_url):
                self.string = string
                self.base_url = base_url

            def write_pdf(self, path):
                Path(path).write_bytes(b"%PDF-1.4 test")

        fake_module = SimpleNamespace(HTML=FakeHtml)

        with override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/", PUBLIC_BASE_URL=""):
            with mock.patch.dict("sys.modules", {"weasyprint": fake_module}):
                output_path = generate_contract_pdf(self.contract.id)

        self.contract.refresh_from_db()
        self.assertTrue(Path(output_path).exists())
        self.assertTrue(self.contract.pdf_file_url.startswith("/media/contracts/"))
        self.assertIsNotNone(self.contract.pdf_generated_at)
        self.assertEqual(self.contract.status, ContractStatus.GENERATED)

    def test_generate_contract_pdf_uses_transient_card_details(self):
        media_root = settings.BASE_DIR / "test-media"
        shutil.rmtree(media_root, ignore_errors=True)
        self.addCleanup(lambda: shutil.rmtree(media_root, ignore_errors=True))
        rendered = {}

        class FakeHtml:
            def __init__(self, string, base_url):
                rendered["html"] = string
                self.base_url = base_url

            def write_pdf(self, path):
                Path(path).write_bytes(b"%PDF-1.4 test")

        fake_module = SimpleNamespace(HTML=FakeHtml)

        with override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/", PUBLIC_BASE_URL=""):
            with mock.patch.dict("sys.modules", {"weasyprint": fake_module}):
                generate_contract_pdf(
                    self.contract.id,
                    payment_details={
                        "credit_card_number": "4111111111111111",
                        "card_csc": "123",
                    },
                )

        self.contract.refresh_from_db()
        self.assertIn("4111111111111111", rendered["html"])
        self.assertIn("123", rendered["html"])
        self.assertFalse(hasattr(self.contract, "credit_card_number"))
        self.assertFalse(hasattr(self.contract, "card_csc"))

    def test_submit_contract_sends_pdf_without_text_summary(self):
        self.technician.telegram_group_chat_id = "-1001234567890"
        self.technician.save(update_fields=["telegram_group_chat_id", "updated_at"])
        media_root = settings.BASE_DIR / "test-media"
        shutil.rmtree(media_root, ignore_errors=True)
        self.addCleanup(lambda: shutil.rmtree(media_root, ignore_errors=True))

        payload = {
            "technician": self.technician.id,
            "contract_date": date(2026, 5, 2),
            "customer_name": "PDF Customer",
            "customer_address": "500 Contract Ave",
            "customer_phone": "555-2222",
            "project_type": CleaningProjectType.AIR_DUCT_CLEANING,
            "subtotal": "250.00",
            "sales_tax": "20.63",
        }

        def fake_generate(contract_id, *, payment_details=None):
            contract = ServiceContract.objects.get(id=contract_id)
            pdf_dir = media_root / "contracts"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            (pdf_dir / f"{contract.contract_number}.pdf").write_bytes(b"%PDF-1.4 test")
            contract.pdf_file_url = f"/media/contracts/{contract.contract_number}.pdf"
            contract.pdf_generated_at = timezone_now
            contract.status = ContractStatus.GENERATED
            contract.save(update_fields=["pdf_file_url", "pdf_generated_at", "status", "updated_at"])
            return pdf_dir / f"{contract.contract_number}.pdf"

        from django.utils import timezone

        timezone_now = timezone.now()
        with override_settings(MEDIA_ROOT=media_root):
            with mock.patch("contracts.services.generate_contract_pdf", side_effect=fake_generate):
                with mock.patch(
                    "notifications.services.NotificationService.send_text_to_telegram",
                    return_value=True,
                ) as text_send:
                    with mock.patch(
                        "notifications.services.NotificationService.send_document_file_to_telegram",
                        return_value=True,
                    ) as document_send:
                        contract = ContractSubmissionService().submit_contract(payload)

        contract.refresh_from_db()
        text_send.assert_not_called()
        document_send.assert_called_once()
        self.assertEqual(contract.status, ContractStatus.SENT)
        self.assertIsNotNone(contract.telegram_sent_at)

    def test_send_contract_pdf_uploads_local_file_when_available(self):
        from contracts.services import send_contract_pdf_to_telegram
        from django.utils import timezone

        self.technician.telegram_group_chat_id = "-1001234567890"
        self.technician.save(update_fields=["telegram_group_chat_id", "updated_at"])
        media_root = settings.BASE_DIR / "test-media"
        pdf_dir = media_root / "contracts"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f"{self.contract.contract_number}.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 local upload test")
        self.addCleanup(lambda: shutil.rmtree(media_root, ignore_errors=True))

        self.contract.pdf_file_url = "https://example.com/media/contracts/test.pdf"
        self.contract.pdf_generated_at = timezone.now()
        self.contract.save(update_fields=["pdf_file_url", "pdf_generated_at", "updated_at"])

        with override_settings(MEDIA_ROOT=media_root):
            with mock.patch(
                "notifications.services.NotificationService.send_document_file_to_telegram",
                return_value=True,
            ) as file_send:
                with mock.patch(
                    "notifications.services.NotificationService.send_document_to_telegram",
                    return_value=True,
                ) as url_send:
                    sent = send_contract_pdf_to_telegram(self.contract.id)

        self.assertTrue(sent)
        file_send.assert_called_once()
        url_send.assert_not_called()
