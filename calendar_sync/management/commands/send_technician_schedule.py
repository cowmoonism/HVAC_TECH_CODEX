from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from calendar_sync.services import send_technician_schedule


class Command(BaseCommand):
    help = "Send one technician's schedule for a target date to their Telegram group chat."

    def add_arguments(self, parser):
        parser.add_argument("--technician-id", type=int, required=True)
        parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format.")

    def handle(self, *args, **options):
        target_date = parse_date(options["date"])
        if target_date is None:
            raise CommandError("--date must use YYYY-MM-DD.")

        summary = send_technician_schedule(
            technician_id=options["technician_id"],
            target_date=target_date,
        )
        self.stdout.write(str(summary))
