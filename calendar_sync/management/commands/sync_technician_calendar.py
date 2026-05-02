from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from calendar_sync.services import sync_google_calendar_for_technician


class Command(BaseCommand):
    help = "Sync Google Calendar events for one technician into CalendarEvent records."

    def add_arguments(self, parser):
        parser.add_argument("--technician-id", type=int, required=True)
        parser.add_argument("--days-ahead", type=int, default=14)

    def handle(self, *args, **options):
        days_ahead = options["days_ahead"]
        if days_ahead < 0:
            raise CommandError("--days-ahead must be zero or greater.")

        start_date = timezone.localdate() - timedelta(days=1)
        end_date = timezone.localdate() + timedelta(days=days_ahead)
        summary = sync_google_calendar_for_technician(
            technician_id=options["technician_id"],
            start_date=start_date,
            end_date=end_date,
        )
        self.stdout.write(str(summary))
        if summary.get("error"):
            raise CommandError(summary["error"])
