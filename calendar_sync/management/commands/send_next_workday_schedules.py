from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from calendar_sync.services import send_technician_schedule
from technicians.models import Technician, TechnicianStatus


class Command(BaseCommand):
    help = "Send next working day schedules to all active technicians with Telegram group chats."

    def handle(self, *args, **options):
        target_date = self._next_working_day(timezone.localdate())
        technicians = Technician.objects.filter(
            status=TechnicianStatus.ACTIVE,
        ).exclude(telegram_group_chat_id="")

        sent_count = 0
        error_count = 0
        for technician in technicians:
            summary = send_technician_schedule(technician.id, target_date)
            self.stdout.write(str(summary))
            if summary.get("sent"):
                sent_count += 1
            if summary.get("error"):
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {technicians.count()} technicians for {target_date}; sent={sent_count}; errors={error_count}."
            )
        )

    def _next_working_day(self, today):
        if today.weekday() == 5:
            return today + timedelta(days=2)
        if today.weekday() == 6:
            return today + timedelta(days=1)
        return today + timedelta(days=1)
