from datetime import timedelta

from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import status, views
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from calendar_sync.models import CalendarEvent
from calendar_sync.permissions import CalendarEventPermission
from calendar_sync.serializers import CalendarEventSerializer
from calendar_sync.services import send_technician_schedule, sync_google_calendar_for_technician


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [CalendarEventPermission]

    def get_queryset(self):
        queryset = CalendarEvent.objects.select_related("technician").all()
        params = self.request.query_params

        technician = params.get("technician")
        if technician:
            queryset = queryset.filter(technician_id=technician)

        status = params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        event_type = params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        start_after = params.get("start_after")
        if start_after:
            queryset = queryset.filter(start_at__gte=self._parse_datetime_param("start_after", start_after))

        start_before = params.get("start_before")
        if start_before:
            queryset = queryset.filter(start_at__lte=self._parse_datetime_param("start_before", start_before))

        return queryset

    def _parse_datetime_param(self, name, value):
        parsed = parse_datetime(value)
        if parsed is None:
            raise ValidationError({name: "Use an ISO 8601 datetime value."})
        return parsed


class SyncTechnicianCalendarView(views.APIView):
    permission_classes = [CalendarEventPermission]

    def post(self, request):
        technician_id = request.data.get("technician_id")
        if not technician_id:
            raise ValidationError({"technician_id": "This field is required."})

        days_ahead = request.data.get("days_ahead", 14)
        try:
            days_ahead = int(days_ahead)
        except (TypeError, ValueError):
            raise ValidationError({"days_ahead": "Use an integer number of days."})
        if days_ahead < 0:
            raise ValidationError({"days_ahead": "Use a non-negative integer."})

        start_date = timezone.localdate() - timedelta(days=1)
        end_date = timezone.localdate() + timedelta(days=days_ahead)
        summary = sync_google_calendar_for_technician(
            technician_id=technician_id,
            start_date=start_date,
            end_date=end_date,
        )
        response_status = status.HTTP_200_OK
        if summary.get("error"):
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(summary, status=response_status)


class SendTechnicianScheduleView(views.APIView):
    permission_classes = [CalendarEventPermission]

    def post(self, request):
        technician_id = request.data.get("technician_id")
        target_date = request.data.get("date")
        if not technician_id:
            raise ValidationError({"technician_id": "This field is required."})
        if not target_date:
            raise ValidationError({"date": "This field is required."})

        summary = send_technician_schedule(technician_id=technician_id, target_date=target_date)
        response_status = status.HTTP_200_OK
        if summary.get("error"):
            response_status = status.HTTP_400_BAD_REQUEST
        return Response(summary, status=response_status)
