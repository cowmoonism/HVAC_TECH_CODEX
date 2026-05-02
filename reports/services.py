import logging

from django.utils import timezone

from calendar_sync.services import update_google_event_description
from notifications.services import NotificationService, get_technician_group_chat
from reports.models import WorkReport
from reports.serializers import WorkReportSerializer


logger = logging.getLogger(__name__)


def send_report_to_telegram(work_report_id):
    work_report = WorkReport.objects.select_related("technician", "calendar_event").get(id=work_report_id)
    chat_id = get_technician_group_chat(work_report.technician)
    message = work_report.build_telegram_message()
    logger.info("Attempting to send work report %s to Telegram chat %s.", work_report.id, chat_id)
    sent = NotificationService().send_text_to_telegram(chat_id=chat_id, text=message)
    if sent:
        work_report.telegram_sent_at = timezone.now()
        work_report.save(update_fields=["telegram_sent_at", "updated_at"])
        logger.info("Work report %s sent to Telegram chat %s.", work_report.id, chat_id)
    else:
        logger.error("Work report %s was not sent to Telegram chat %s.", work_report.id, chat_id)
    return sent


def update_calendar_event_with_report(work_report_id):
    work_report = WorkReport.objects.select_related("calendar_event", "technician").get(id=work_report_id)
    if not work_report.calendar_event_id:
        logger.info("Work report %s has no calendar event; Google Calendar update skipped.", work_report.id)
        return False

    appended_text = work_report.build_calendar_description_block()
    updated = update_google_event_description(work_report.calendar_event_id, appended_text)
    if updated:
        work_report.calendar_updated_at = timezone.now()
        work_report.save(update_fields=["calendar_updated_at", "updated_at"])
        logger.info("Work report %s appended to Google Calendar event %s.", work_report.id, work_report.calendar_event_id)
    else:
        logger.error("Work report %s was not appended to Google Calendar event %s.", work_report.id, work_report.calendar_event_id)
    return updated


class ReportSubmissionService:
    def submit_report(self, data: dict):
        serializer = WorkReportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        work_report = serializer.save()

        try:
            send_report_to_telegram(work_report.id)
        except Exception as exc:
            logger.error("Report Telegram notification failed for report %s: %s", work_report.id, exc, exc_info=True)

        try:
            update_calendar_event_with_report(work_report.id)
        except Exception as exc:
            logger.error("Report calendar update failed for report %s: %s", work_report.id, exc, exc_info=True)

        return work_report
