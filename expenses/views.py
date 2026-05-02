from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from expenses.models import ExpenseReport
from expenses.permissions import ExpenseReportPermission
from expenses.serializers import ExpenseReportSerializer
from expenses.services import ExpenseSubmissionService


class ExpenseReportViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseReportSerializer
    permission_classes = [ExpenseReportPermission]

    def get_queryset(self):
        queryset = ExpenseReport.objects.select_related("technician", "calendar_event").all()
        params = self.request.query_params

        technician = params.get("technician")
        if technician:
            queryset = queryset.filter(technician_id=technician)

        calendar_event = params.get("calendar_event")
        if calendar_event:
            queryset = queryset.filter(calendar_event_id=calendar_event)

        expense_date = params.get("expense_date")
        if expense_date:
            queryset = queryset.filter(expense_date=expense_date)

        expense_type = params.get("expense_type")
        if expense_type:
            queryset = queryset.filter(expense_type=expense_type)

        created_after = params.get("created_after")
        if created_after:
            queryset = queryset.filter(created_at__gte=self._parse_datetime_param("created_after", created_after))

        created_before = params.get("created_before")
        if created_before:
            queryset = queryset.filter(created_at__lte=self._parse_datetime_param("created_before", created_before))

        return queryset

    def create(self, request, *args, **kwargs):
        expense_report = ExpenseSubmissionService().submit_expense(request.data)
        serializer = self.get_serializer(expense_report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _parse_datetime_param(self, name, value):
        parsed = parse_datetime(value)
        if parsed is None:
            raise ValidationError({name: "Use an ISO 8601 datetime value."})
        return parsed
