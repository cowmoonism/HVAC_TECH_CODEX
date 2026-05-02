from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.serializers import ServiceContractSerializer
from contracts.services import ContractSubmissionService
from expenses.serializers import ExpenseReportSerializer
from expenses.services import ExpenseSubmissionService
from reports.serializers import WorkReportSerializer
from reports.services import ReportSubmissionService
from technicians.submission_serializers import (
    TechnicianContractSubmissionSerializer,
    TechnicianExpenseSubmissionSerializer,
    TechnicianWorkReportSubmissionSerializer,
)
from technicians.telegram_auth import TelegramWebAppAuthError, validate_telegram_webapp_init_data


class TechnicianSubmissionAuthMixin:
    permission_classes = [AllowAny]

    def authenticate_submission(self, request):
        init_data = request.headers.get("X-Telegram-WebApp-InitData", "")
        if init_data:
            try:
                parsed_data = validate_telegram_webapp_init_data(init_data, settings.TECHNICIAN_BOT_TOKEN)
            except TelegramWebAppAuthError as exc:
                return None, Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

            user = parsed_data.get("user") or {}
            telegram_user_id = user.get("id")
            if not telegram_user_id:
                return None, Response(
                    {"detail": "Telegram WebApp initData does not include user.id."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            data = request.data.copy()
            data["telegram_user_id"] = str(telegram_user_id)
            return data, None

        if not settings.DEBUG:
            return None, Response(
                {"detail": "Telegram WebApp initData is required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        expected_secret = settings.TECHNICIAN_API_SHARED_SECRET
        if not expected_secret:
            return None, Response(
                {"detail": "Technician submission API secret is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        provided_secret = request.headers.get("X-Technician-Api-Secret", "")
        if provided_secret != expected_secret:
            return None, Response(
                {"detail": "Invalid technician submission API secret."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return request.data, None


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
