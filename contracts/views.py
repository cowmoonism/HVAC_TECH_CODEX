from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from contracts.models import ServiceContract
from contracts.permissions import ServiceContractPermission
from contracts.serializers import ServiceContractSerializer
from contracts.services import ContractSubmissionService


class ServiceContractViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceContractSerializer
    permission_classes = [ServiceContractPermission]

    def get_queryset(self):
        queryset = ServiceContract.objects.select_related("technician", "calendar_event").all()
        params = self.request.query_params

        technician = params.get("technician")
        if technician:
            queryset = queryset.filter(technician_id=technician)

        calendar_event = params.get("calendar_event")
        if calendar_event:
            queryset = queryset.filter(calendar_event_id=calendar_event)

        contract_date = params.get("contract_date")
        if contract_date:
            queryset = queryset.filter(contract_date=contract_date)

        status_value = params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        created_after = params.get("created_after")
        if created_after:
            queryset = queryset.filter(created_at__gte=self._parse_datetime_param("created_after", created_after))

        created_before = params.get("created_before")
        if created_before:
            queryset = queryset.filter(created_at__lte=self._parse_datetime_param("created_before", created_before))

        return queryset

    def create(self, request, *args, **kwargs):
        service_contract = ContractSubmissionService().submit_contract(request.data)
        serializer = self.get_serializer(service_contract)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _parse_datetime_param(self, name, value):
        parsed = parse_datetime(value)
        if parsed is None:
            raise ValidationError({name: "Use an ISO 8601 datetime value."})
        return parsed
