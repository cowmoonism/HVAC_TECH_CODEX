from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from calendar_sync.models import CalendarEvent, CalendarEventStatus, CalendarEventType
from contracts.serializers import ServiceContractSerializer
from contracts.services import ContractSubmissionService
from expenses.serializers import ExpenseReportSerializer
from expenses.services import ExpenseSubmissionService
from reports.models import WorkReport
from reports.serializers import WorkReportSerializer
from reports.services import ReportSubmissionService
from technicians.form_tokens import TechnicianFormTokenError, validate_technician_form_token
from technicians.models import Technician
from technicians.submission_serializers import (
    TechnicianContractSubmissionSerializer,
    TechnicianExpenseSubmissionSerializer,
    TechnicianWorkReportSubmissionSerializer,
)
from technicians.telegram_auth import TelegramWebAppAuthError, validate_telegram_webapp_init_data


class TechnicianSubmissionAuthMixin:
    permission_classes = [AllowAny]

    def authenticate_technician_identity(self, request):
        form_token = request.headers.get("X-Technician-Form-Token", "")
        if form_token:
            try:
                token_data = validate_technician_form_token(form_token, settings.TECHNICIAN_API_SHARED_SECRET)
            except TechnicianFormTokenError as exc:
                return None, None, Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

            telegram_user_id = token_data.get("telegram_user_id")
            if not telegram_user_id:
                return None, None, Response(
                    {"detail": "Technician form token does not include telegram_user_id."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return str(telegram_user_id), token_data.get("telegram_group_chat_id"), None

        init_data = request.headers.get("X-Telegram-WebApp-InitData", "")
        if init_data:
            try:
                parsed_data = validate_telegram_webapp_init_data(init_data, settings.TECHNICIAN_BOT_TOKEN)
            except TelegramWebAppAuthError as exc:
                return None, None, Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

            user = parsed_data.get("user") or {}
            telegram_user_id = user.get("id")
            if not telegram_user_id:
                return None, None, Response(
                    {"detail": "Telegram WebApp initData does not include user.id."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return str(telegram_user_id), None, None

        if not settings.DEBUG:
            return None, None, Response(
                {"detail": "Telegram WebApp initData is required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        expected_secret = settings.TECHNICIAN_API_SHARED_SECRET
        if not expected_secret:
            return None, None, Response(
                {"detail": "Technician submission API secret is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        provided_secret = request.headers.get("X-Technician-Api-Secret", "")
        if provided_secret != expected_secret:
            return None, None, Response(
                {"detail": "Invalid technician submission API secret."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return request.data.get("telegram_user_id"), request.data.get("telegram_group_chat_id"), None

    def authenticate_submission(self, request):
        telegram_user_id, telegram_group_chat_id, auth_response = self.authenticate_technician_identity(request)
        if auth_response is not None:
            return None, auth_response
        data = request.data.copy()
        data["telegram_user_id"] = str(telegram_user_id)
        if telegram_group_chat_id:
            data["telegram_group_chat_id"] = str(telegram_group_chat_id)
        return data, None

    def get_authenticated_technician(self, request):
        telegram_user_id, telegram_group_chat_id, auth_response = self.authenticate_technician_identity(request)
        if auth_response is not None:
            return None, None, auth_response
        try:
            technician = Technician.objects.get(telegram_user_id=str(telegram_user_id))
        except Technician.DoesNotExist:
            return None, None, Response(
                {"detail": f"No technician found for Telegram user id {telegram_user_id}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return technician, telegram_group_chat_id, None


class TechnicianCalendarEventsView(TechnicianSubmissionAuthMixin, APIView):
    def get(self, request):
        technician, _telegram_group_chat_id, auth_response = self.get_authenticated_technician(request)
        if auth_response is not None:
            return auth_response

        now = timezone.localtime()
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        try:
            days_ahead = int(request.query_params.get("days_ahead") or 14)
        except ValueError:
            return Response({"detail": "days_ahead must be a number."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if start_date:
                start_at = timezone.make_aware(datetime.fromisoformat(start_date))
            else:
                start_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if end_date:
                end_at = timezone.make_aware(datetime.fromisoformat(end_date)).replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            else:
                end_at = start_at + timedelta(days=days_ahead)
        except ValueError:
            return Response(
                {"detail": "start_date and end_date must use YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        events = (
            CalendarEvent.objects.filter(
                technician=technician,
                event_type=CalendarEventType.JOB,
                start_at__gte=start_at,
                start_at__lte=end_at,
            )
            .exclude(
                status__in=[
                    CalendarEventStatus.CANCELED,
                    CalendarEventStatus.RESCHEDULED,
                    CalendarEventStatus.FAKE,
                ]
            )
            .order_by("start_at")
        )
        report_counts = dict(
            WorkReport.objects.filter(calendar_event__in=events)
            .values_list("calendar_event_id")
            .annotate(count=Count("id"))
        )

        payload = []
        for event in events:
            local_start = timezone.localtime(event.start_at)
            local_end = timezone.localtime(event.end_at)
            payload.append(
                {
                    "id": event.id,
                    "google_event_id": event.google_event_id,
                    "title": event.clean_title_for_technician(),
                    "raw_title": event.title,
                    "location": event.location,
                    "start_at": event.start_at.isoformat(),
                    "end_at": event.end_at.isoformat(),
                    "start_label": local_start.strftime("%a, %b %d %I:%M %p").replace(" 0", " "),
                    "time_label": (
                        f"{local_start.strftime('%I:%M %p').lstrip('0')} - "
                        f"{local_end.strftime('%I:%M %p').lstrip('0')}"
                    ),
                    "job_number": event.job_number or "",
                    "report_count": report_counts.get(event.id, 0),
                }
            )
        return Response({"technician_id": technician.id, "events": payload})


class SubmitWorkReportView(TechnicianSubmissionAuthMixin, APIView):
    def post(self, request):
        submission_data, auth_response = self.authenticate_submission(request)
        if auth_response is not None:
            return auth_response

        serializer = TechnicianWorkReportSubmissionSerializer(data=submission_data)
        serializer.is_valid(raise_exception=True)
        work_report = ReportSubmissionService().submit_report(serializer.to_service_data())
        return Response(WorkReportSerializer(work_report).data, status=status.HTTP_201_CREATED)


class SubmitExpenseView(TechnicianSubmissionAuthMixin, APIView):
    def post(self, request):
        submission_data, auth_response = self.authenticate_submission(request)
        if auth_response is not None:
            return auth_response

        serializer = TechnicianExpenseSubmissionSerializer(data=submission_data)
        serializer.is_valid(raise_exception=True)
        expense_report = ExpenseSubmissionService().submit_expense(serializer.to_service_data())
        return Response(ExpenseReportSerializer(expense_report).data, status=status.HTTP_201_CREATED)


class SubmitContractView(TechnicianSubmissionAuthMixin, APIView):
    def post(self, request):
        submission_data, auth_response = self.authenticate_submission(request)
        if auth_response is not None:
            return auth_response

        serializer = TechnicianContractSubmissionSerializer(data=submission_data)
        serializer.is_valid(raise_exception=True)
        service_contract = ContractSubmissionService().submit_contract(serializer.to_service_data())
        return Response(ServiceContractSerializer(service_contract).data, status=status.HTTP_201_CREATED)
