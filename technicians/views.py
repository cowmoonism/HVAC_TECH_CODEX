from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from technicians.models import Technician, TechnicianStatus
from technicians.permissions import TechnicianEndpointPermission
from technicians.serializers import TechnicianSerializer


class TechnicianViewSet(viewsets.ModelViewSet):
    queryset = Technician.objects.all()
    serializer_class = TechnicianSerializer
    permission_classes = [TechnicianEndpointPermission]

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        technician = self.get_object()
        missing_fields = []
        if not technician.telegram_user_id:
            missing_fields.append("telegram_user_id")
        if not technician.telegram_group_chat_id:
            missing_fields.append("telegram_group_chat_id")
        if not technician.google_calendar_id:
            missing_fields.append("google_calendar_id")

        if missing_fields:
            return Response(
                {
                    "detail": "Technician cannot be activated until required integration fields are set.",
                    "missing_fields": missing_fields,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        technician.status = TechnicianStatus.ACTIVE
        technician.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(technician).data)
