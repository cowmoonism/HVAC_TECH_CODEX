import logging
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from audit.services import log_audit_event
from config.url_utils import build_public_url
from contracts.models import ContractStatus, ServiceContract
from contracts.serializers import ServiceContractSerializer
from notifications.services import NotificationService, get_technician_group_chat


logger = logging.getLogger(__name__)


def generate_contract_pdf(service_contract_id, *, payment_details=None):
    from weasyprint import HTML

    service_contract = ServiceContract.objects.select_related("technician", "calendar_event").get(id=service_contract_id)
    html = render_to_string(
        "contracts/service_contract_pdf.html",
        {
            "contract": service_contract,
            "payment_details": payment_details or {},
        },
    )
    output_dir = Path(settings.MEDIA_ROOT) / "contracts"
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{service_contract.contract_number}.pdf"
    output_path = output_dir / file_name
    HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(str(output_path))

    service_contract.pdf_file_url = build_public_url(f"{settings.MEDIA_URL}contracts/{file_name}")
    service_contract.pdf_generated_at = timezone.now()
    if service_contract.status not in {ContractStatus.SENT, ContractStatus.SIGNED}:
        service_contract.status = ContractStatus.GENERATED
    service_contract.save(
        update_fields=[
            "pdf_file_url",
            "pdf_generated_at",
            "status",
            "updated_at",
        ]
    )
    logger.info("Generated PDF for service contract %s at %s.", service_contract.id, output_path)
    return str(output_path)


def send_contract_pdf_to_telegram(service_contract_id):
    service_contract = ServiceContract.objects.select_related("technician").get(id=service_contract_id)
    if not service_contract.pdf_file_url:
        logger.warning("Service contract %s has no PDF URL; Telegram PDF send skipped.", service_contract.id)
        return False
    public_pdf_url = build_public_url(service_contract.pdf_file_url)
    if public_pdf_url.startswith("/"):
        logger.warning(
            "Service contract %s PDF URL %s is relative and PUBLIC_BASE_URL is missing. Telegram requires a public URL; send skipped.",
            service_contract.id,
            public_pdf_url,
        )
        return False

    chat_id = get_technician_group_chat(service_contract.technician)
    caption = f"Service contract {service_contract.contract_number}"
    sent = NotificationService().send_document_to_telegram(
        chat_id=chat_id,
        file_url=public_pdf_url,
        caption=caption,
    )
    if sent:
        service_contract.telegram_sent_at = timezone.now()
        service_contract.status = ContractStatus.SENT
        service_contract.save(update_fields=["telegram_sent_at", "status", "updated_at"])
        logger.info("Service contract %s PDF sent to Telegram chat %s.", service_contract.id, chat_id)
    else:
        logger.error("Service contract %s PDF was not sent to Telegram chat %s.", service_contract.id, chat_id)
    return sent


def send_contract_summary_to_telegram(service_contract_id):
    service_contract = ServiceContract.objects.select_related("technician", "calendar_event").get(id=service_contract_id)
    chat_id = get_technician_group_chat(service_contract.technician)
    message = service_contract.build_telegram_message()
    logger.info("Attempting to send service contract %s summary to Telegram chat %s.", service_contract.id, chat_id)
    sent = NotificationService().send_text_to_telegram(chat_id=chat_id, text=message)
    if sent:
        service_contract.telegram_sent_at = timezone.now()
        service_contract.save(update_fields=["telegram_sent_at", "updated_at"])
        logger.info("Service contract %s summary sent to Telegram chat %s.", service_contract.id, chat_id)
    else:
        logger.error("Service contract %s summary was not sent to Telegram chat %s.", service_contract.id, chat_id)
    return sent


class ContractSubmissionService:
    def submit_contract(self, data: dict, *, actor=None):
        serializer = ServiceContractSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        service_contract = serializer.save()
        payment_details = serializer.get_sensitive_payment_details()
        log_audit_event(
            "contract.create",
            actor=actor,
            target=f"service_contract:{service_contract.id}",
            metadata={
                "technician_id": service_contract.technician_id,
                "calendar_event_id": service_contract.calendar_event_id,
                "status": service_contract.status,
                "contract_number": service_contract.contract_number,
                "total": service_contract.total,
            },
        )
        try:
            generate_contract_pdf(service_contract.id, payment_details=payment_details)
        except Exception as exc:
            logger.error(
                "Contract PDF generation failed for contract %s: %s",
                service_contract.id,
                exc,
                exc_info=True,
            )

        try:
            send_contract_pdf_to_telegram(service_contract.id)
        except Exception as exc:
            logger.error(
                "Contract Telegram PDF send failed for contract %s: %s",
                service_contract.id,
                exc,
                exc_info=True,
            )

        service_contract.refresh_from_db()
        return service_contract
