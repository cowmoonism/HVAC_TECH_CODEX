import logging

from django.utils import timezone

from expenses.models import ExpenseReport
from expenses.serializers import ExpenseReportSerializer
from notifications.services import NotificationService, get_technician_group_chat


logger = logging.getLogger(__name__)


def send_expense_to_telegram(expense_report_id):
    expense_report = ExpenseReport.objects.select_related("technician", "calendar_event").get(id=expense_report_id)
    chat_id = get_technician_group_chat(expense_report.technician)
    message = expense_report.build_telegram_message()
    logger.info("Attempting to send expense report %s to Telegram chat %s.", expense_report.id, chat_id)
    sent = NotificationService().send_text_to_telegram(chat_id=chat_id, text=message)
    if sent:
        expense_report.telegram_sent_at = timezone.now()
        expense_report.save(update_fields=["telegram_sent_at", "updated_at"])
        logger.info("Expense report %s sent to Telegram chat %s.", expense_report.id, chat_id)
    else:
        logger.error("Expense report %s was not sent to Telegram chat %s.", expense_report.id, chat_id)
    return sent


class ExpenseSubmissionService:
    def submit_expense(self, data: dict):
        serializer = ExpenseReportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        expense_report = serializer.save()
        try:
            send_expense_to_telegram(expense_report.id)
        except Exception as exc:
            logger.error(
                "Expense Telegram notification failed for expense %s: %s",
                expense_report.id,
                exc,
                exc_info=True,
            )
        return expense_report
