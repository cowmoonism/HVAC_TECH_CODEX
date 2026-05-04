from datetime import date
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from contracts.models import CleaningProjectType, ContractStatus, ServiceContract
from contracts.services import generate_contract_pdf
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
