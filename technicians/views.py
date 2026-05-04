from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.services import log_audit_event
from technicians.models import (
    Technician,
    TechnicianStatus,
    TechnicianTelegramRegistration,
    TechnicianTelegramRegistrationStatus,
)
from technicians.permissions import TechnicianEndpointPermission
from technicians.serializers import (
    TechnicianSerializer,
    TechnicianTelegramRegistrationSerializer,
)


class TechnicianViewSet(viewsets.ModelViewSet):
    queryset = Technician.objects.all()
    serializer_class = TechnicianSerializer
    permission_classes = [TechnicianEndpointPermission]

    def perform_create(self, serializer):
        technician = serializer.save()
        log_audit_event(
            "technician.create",
            actor=self.request.user,
            target=f"technician:{technician.id}",
            metadata={
                "status": technician.status,
                "has_telegram_user_id": bool(technician.telegram_user_id),
                "has_group_chat_id": bool(technician.telegram_group_chat_id),
                "has_google_calendar_id": bool(technician.google_calendar_id),
            },
        )

    def perform_update(self, serializer):
        technician = serializer.save()
        log_audit_event(
            "technician.update",
            actor=self.request.user,
            target=f"technician:{technician.id}",
            metadata={
                "status": technician.status,
                "has_telegram_user_id": bool(technician.telegram_user_id),
                "has_group_chat_id": bool(technician.telegram_group_chat_id),
                "has_google_calendar_id": bool(technician.google_calendar_id),
            },
        )

    @action(detail=True, methods=["post"], url_path="start-telegram-registration")
    def start_telegram_registration(self, request, pk=None):
        technician = self.get_object()
        TechnicianTelegramRegistration.objects.filter(
            technician=technician,
            status__in=[
                TechnicianTelegramRegistrationStatus.PENDING,
                TechnicianTelegramRegistrationStatus.CLAIMED,
            ],
        ).update(status=TechnicianTelegramRegistrationStatus.SUPERSEDED, updated_at=timezone.now())
        registration = TechnicianTelegramRegistration.objects.create(technician=technician)
        log_audit_event(
            "technician.telegram_registration.start",
            actor=request.user,
            target=f"technician:{technician.id}",
            metadata={"registration_id": registration.id},
        )
        return Response(TechnicianTelegramRegistrationSerializer(registration).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="telegram-registration")
    def telegram_registration(self, request, pk=None):
        technician = self.get_object()
        registration = technician.telegram_registrations.order_by("-created_at").first()
        if registration is None:
            return Response(
                {
                    "status": "NOT_STARTED",
                    "token": "",
                    "telegram_user_id": "",
                    "telegram_username": "",
                    "telegram_group_chat_id": "",
                    "telegram_group_title": "",
                    "telegram_chat_type": "",
                    "claimed_at": None,
                    "linked_at": None,
                    "created_at": None,
                    "updated_at": None,
                    "bot_start_url": "",
                }
            )
        return Response(TechnicianTelegramRegistrationSerializer(registration).data)

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

        duplicate = (
            Technician.objects.filter(google_calendar_id=technician.google_calendar_id)
            .exclude(pk=technician.pk)
            .first()
        )
        if duplicate:
            return Response(
                {
                    "detail": "Technician cannot be activated because this Google Calendar ID is already assigned to another technician.",
                    "google_calendar_id": "A technician with this Google Calendar ID already exists.",
                    "conflicting_technician_id": duplicate.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        technician.status = TechnicianStatus.ACTIVE
        technician.save(update_fields=["status", "updated_at"])
        log_audit_event(
            "technician.activate",
            actor=request.user,
            target=f"technician:{technician.id}",
            metadata={"status": technician.status},
        )
        return Response(self.get_serializer(technician).data)
