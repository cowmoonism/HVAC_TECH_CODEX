from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from reports.models import WorkReport
from reports.permissions import WorkReportPermission, WorkReportSummaryPermission
from reports.serializers import WorkReportSerializer
from reports.services import ReportSubmissionService
from reports.summary import build_daily_summary, build_weekly_summary


class WorkReportViewSet(viewsets.ModelViewSet):
    serializer_class = WorkReportSerializer
    permission_classes = [WorkReportPermission]

    def get_queryset(self):
        queryset = WorkReport.objects.select_related("technician", "calendar_event").all()
        params = self.request.query_params

        technician = params.get("technician")
        if technician:
            queryset = queryset.filter(technician_id=technician)

        calendar_event = params.get("calendar_event")
        if calendar_event:
            queryset = queryset.filter(calendar_event_id=calendar_event)

        report_date = params.get("report_date")
        if report_date:
            queryset = queryset.filter(report_date=report_date)

        payment_type = params.get("payment_type")
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)

        created_after = params.get("created_after")
        if created_after:
            queryset = queryset.filter(created_at__gte=self._parse_datetime_param("created_after", created_after))

        created_before = params.get("created_before")
        if created_before:
            queryset = queryset.filter(created_at__lte=self._parse_datetime_param("created_before", created_before))

        return queryset

    def create(self, request, *args, **kwargs):
        work_report = ReportSubmissionService().submit_report(request.data, actor=request.user)
        serializer = self.get_serializer(work_report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _parse_datetime_param(self, name, value):
        parsed = parse_datetime(value)
        if parsed is None:
            raise ValidationError({name: "Use an ISO 8601 datetime value."})
        return parsed


class DailySummaryView(APIView):
    permission_classes = [WorkReportSummaryPermission]

    def get(self, request):
        target_date = parse_date(request.query_params.get("date", ""))
        if target_date is None:
            raise ValidationError({"date": "Use YYYY-MM-DD."})

        technician = self._parse_optional_technician(request.query_params.get("technician"))
        summary = build_daily_summary(target_date=target_date, technician_id=technician)
        return Response(summary)

    def _parse_optional_technician(self, value):
        if value in {None, ""}:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({"technician": "Use an integer technician id."})


class WeeklySummaryView(APIView):
    permission_classes = [WorkReportSummaryPermission]

    def get(self, request):
        week_start = parse_date(request.query_params.get("week_start", ""))
        if week_start is None:
            raise ValidationError({"week_start": "Use YYYY-MM-DD."})

        technician = self._parse_optional_technician(request.query_params.get("technician"))
        summary = build_weekly_summary(week_start=week_start, technician_id=technician)
        return Response(summary)

    def _parse_optional_technician(self, value):
        if value in {None, ""}:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({"technician": "Use an integer technician id."})
