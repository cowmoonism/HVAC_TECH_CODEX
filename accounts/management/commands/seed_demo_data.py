from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import UserRole
from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from contracts.models import CleaningProjectType, ServiceContract
from expenses.models import ExpenseReport, ExpenseType
from reports.models import ClosedBy, PaymentType, ReviewStatus, WorkReport
from technicians.models import Technician, TechnicianStatus


class Command(BaseCommand):
    help = "Seed demo users, technician data, events, reports, expenses, and a contract."

    def handle(self, *args, **options):
        manager = self._upsert_user("manager", "password", UserRole.MANAGER)
        callcenter = self._upsert_user("callcenter", "password", UserRole.CALL_CENTER)
        accountant = self._upsert_user("accountant", "password", UserRole.ACCOUNTANT)

        technician, _ = Technician.objects.get_or_create(
            email="demo.tech@example.com",
            defaults={
                "first_name": "Demo",
                "last_name": "Technician",
                "display_name": "Demo Technician",
                "phone": "555-1000",
                "status": TechnicianStatus.ACTIVE,
                "service_state": "CA",
                "timezone": "America/Los_Angeles",
                "telegram_user_id": "900001",
                "telegram_username": "demo_tech",
                "telegram_group_chat_id": "-100900001",
                "google_calendar_id": "demo.tech.calendar@example.com",
                "notes": "Seeded demo technician",
            },
        )

        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        start_one = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()).replace(hour=9))
        end_one = start_one + timedelta(hours=2)
        start_two = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()).replace(hour=12))
        end_two = start_two + timedelta(hours=2)

        event_one, _ = CalendarEvent.objects.get_or_create(
            google_calendar_id=technician.google_calendar_id,
            google_event_id="demo-event-1",
            defaults={
                "technician": technician,
                "event_type": CalendarEventType.JOB,
                "status": CalendarEventStatus.SCHEDULED,
                "title": "1. Demo Duct Cleaning",
                "location": "123 Demo St",
                "description": "Seeded demo event",
                "start_at": start_one,
                "end_at": end_one,
                "timezone": technician.timezone,
                "job_number": "DEMO-1",
            },
        )
        event_two, _ = CalendarEvent.objects.get_or_create(
            google_calendar_id=technician.google_calendar_id,
            google_event_id="demo-event-2",
            defaults={
                "technician": technician,
                "event_type": CalendarEventType.JOB,
                "status": CalendarEventStatus.SCHEDULED,
                "title": "2. Demo Maintenance",
                "location": "456 Demo Ave",
                "description": "Seeded demo event",
                "start_at": start_two,
                "end_at": end_two,
                "timezone": technician.timezone,
                "job_number": "DEMO-2",
            },
        )

        WorkReport.objects.get_or_create(
            technician=technician,
            report_date=today,
            job_number="DEMO-REPORT-1",
            defaults={
                "calendar_event": event_one,
                "address": "123 Demo St",
                "payment_type": PaymentType.CASH,
                "amount": Decimal("150.00"),
                "closed_by": ClosedBy.TECHNICIAN,
                "project_description": "Seeded demo cleaning report",
                "groupon_review": ReviewStatus.NO,
                "google_review": ReviewStatus.YES,
                "yearly_maintenance_plan": ReviewStatus.YES,
            },
        )
        WorkReport.objects.get_or_create(
            technician=technician,
            report_date=today,
            job_number="DEMO-REPORT-2",
            defaults={
                "calendar_event": event_two,
                "address": "456 Demo Ave",
                "payment_type": PaymentType.ESTIMATE,
                "amount": Decimal("999.00"),
                "closed_by": ClosedBy.MANAGER,
                "project_description": "Seeded demo estimate report",
                "groupon_review": ReviewStatus.YES,
                "google_review": ReviewStatus.NO,
                "yearly_maintenance_plan": ReviewStatus.NO,
            },
        )

        ExpenseReport.objects.get_or_create(
            technician=technician,
            expense_date=today,
            expense_type=ExpenseType.GAS,
            defaults={
                "calendar_event": event_one,
                "amount": Decimal("25.00"),
                "description": "Seeded fuel expense",
            },
        )
        ExpenseReport.objects.get_or_create(
            technician=technician,
            expense_date=today,
            expense_type=ExpenseType.MATERIALS,
            defaults={
                "calendar_event": event_two,
                "amount": Decimal("40.00"),
                "description": "Seeded materials expense",
            },
        )

        contract = ServiceContract.objects.filter(
            technician=technician,
            contract_date=today,
            customer_name="Demo Customer",
        ).first()
        if contract is None:
            ServiceContract.objects.create(
                technician=technician,
                calendar_event=event_one,
                contract_date=today,
                customer_name="Demo Customer",
                customer_address="123 Demo St",
                customer_phone="555-2000",
                project_type=CleaningProjectType.AIR_DUCT_CLEANING,
                project_description="Seeded demo contract",
                subtotal=Decimal("300.00"),
                sales_tax=Decimal("24.75"),
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo data for users: {manager.username}, {callcenter.username}, {accountant.username}; technician: {technician}."
            )
        )

    def _upsert_user(self, username, password, role):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.com"},
        )
        user.set_password(password)
        user.save(update_fields=["password"])
        user.profile.role = role
        user.profile.save(update_fields=["role", "updated_at"])
        return user
