from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit_event
from technicians.models import (
    Technician,
    TechnicianTelegramRegistration,
    TechnicianTelegramRegistrationStatus,
)
from technicians.validators import validate_telegram_numeric


def _bot_secret_is_valid(request) -> bool:
    configured = getattr(settings, "TECHNICIAN_API_SHARED_SECRET", "")
    if not configured:
        return False
    return request.headers.get("X-Technician-Bot-Secret", "") == configured


class TechnicianBotRegistrationBaseView(APIView):
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        configured = getattr(settings, "TECHNICIAN_API_SHARED_SECRET", "")
        if not configured:
            return Response({"detail": "Technician bot secret is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if not _bot_secret_is_valid(request):
            return Response({"detail": "Invalid technician bot secret."}, status=status.HTTP_403_FORBIDDEN)
        return super().dispatch(request, *args, **kwargs)


class ClaimTelegramRegistrationView(TechnicianBotRegistrationBaseView):
    def post(self, request):
        token = str(request.data.get("token", "")).strip()
        telegram_user_id = str(request.data.get("telegram_user_id", "")).strip()
        telegram_username = str(request.data.get("telegram_username", "")).strip()

        if not token:
            return Response({"token": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        if not telegram_user_id:
            return Response({"telegram_user_id": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_telegram_numeric(telegram_user_id, "telegram_user_id")
        except Exception as exc:
            return Response({"telegram_user_id": exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        registration = TechnicianTelegramRegistration.objects.filter(token=token).select_related("technician").first()
        if registration is None:
            return Response({"detail": "Registration token is invalid."}, status=status.HTTP_404_NOT_FOUND)
        if registration.status == TechnicianTelegramRegistrationStatus.SUPERSEDED:
            return Response({"detail": "Registration token has been replaced. Start again from the technician profile."}, status=status.HTTP_409_CONFLICT)
        if registration.status == TechnicianTelegramRegistrationStatus.LINKED:
            return Response({"detail": "Registration token has already been linked."}, status=status.HTTP_409_CONFLICT)

        existing_technician = Technician.objects.filter(telegram_user_id=telegram_user_id).exclude(pk=registration.technician_id).first()
        if existing_technician is not None:
            return Response(
                {"detail": "This Telegram user is already linked to another technician."},
                status=status.HTTP_409_CONFLICT,
            )

        registration.telegram_user_id = telegram_user_id
        registration.telegram_username = telegram_username
        registration.status = TechnicianTelegramRegistrationStatus.CLAIMED
        registration.claimed_at = timezone.now()
        registration.save(
            update_fields=[
                "telegram_user_id",
                "telegram_username",
                "status",
                "claimed_at",
                "updated_at",
            ]
        )
        log_audit_event(
            "technician.telegram_registration.claim",
            target=f"technician:{registration.technician_id}",
            metadata={"registration_id": registration.id},
        )
        return Response(
            {
                "detail": "Registration claimed. Use Complete Registration in your work group chat next.",
                "technician_id": registration.technician_id,
                "registration_status": registration.status,
            }
        )


class CompleteTelegramRegistrationView(TechnicianBotRegistrationBaseView):
    def post(self, request):
        telegram_user_id = str(request.data.get("telegram_user_id", "")).strip()
        telegram_username = str(request.data.get("telegram_username", "")).strip()
        telegram_group_chat_id = str(request.data.get("telegram_group_chat_id", "")).strip()
        telegram_group_title = str(request.data.get("telegram_group_title", "")).strip()
        telegram_chat_type = str(request.data.get("telegram_chat_type", "")).strip()

        if not telegram_user_id or not telegram_group_chat_id:
            return Response(
                {"detail": "telegram_user_id and telegram_group_chat_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if telegram_chat_type not in {"group", "supergroup"}:
            return Response(
                {"detail": "Registration must be completed from a Telegram group or supergroup."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_telegram_numeric(telegram_user_id, "telegram_user_id")
            validate_telegram_numeric(telegram_group_chat_id, "telegram_group_chat_id")
        except Exception as exc:
            detail = exc.detail if hasattr(exc, "detail") else str(exc)
            field = "telegram_user_id" if "user" in str(detail).lower() else "telegram_group_chat_id"
            return Response({field: detail}, status=status.HTTP_400_BAD_REQUEST)

        registration = (
            TechnicianTelegramRegistration.objects.filter(
                telegram_user_id=telegram_user_id,
                status=TechnicianTelegramRegistrationStatus.CLAIMED,
            )
            .select_related("technician")
            .order_by("-created_at")
            .first()
        )
        if registration is None:
            return Response(
                {"detail": "No claimed technician registration was found for this Telegram user. Start from the bot link first."},
                status=status.HTTP_409_CONFLICT,
            )

        other_technician = Technician.objects.filter(telegram_group_chat_id=telegram_group_chat_id).exclude(
            pk=registration.technician_id
        ).first()
        if other_technician is not None:
            return Response(
                {"detail": "This Telegram work group is already linked to another technician."},
                status=status.HTTP_409_CONFLICT,
            )

        technician = registration.technician
        technician.telegram_user_id = telegram_user_id
        technician.telegram_username = telegram_username
        technician.telegram_group_chat_id = telegram_group_chat_id
        technician.save(
            update_fields=[
                "telegram_user_id",
                "telegram_username",
                "telegram_group_chat_id",
                "updated_at",
            ]
        )

        registration.telegram_username = telegram_username
        registration.telegram_group_chat_id = telegram_group_chat_id
        registration.telegram_group_title = telegram_group_title
        registration.telegram_chat_type = telegram_chat_type
        registration.status = TechnicianTelegramRegistrationStatus.LINKED
        registration.linked_at = timezone.now()
        registration.save(
            update_fields=[
                "telegram_username",
                "telegram_group_chat_id",
                "telegram_group_title",
                "telegram_chat_type",
                "status",
                "linked_at",
                "updated_at",
            ]
        )

        TechnicianTelegramRegistration.objects.filter(
            technician=technician,
            status__in=[
                TechnicianTelegramRegistrationStatus.PENDING,
                TechnicianTelegramRegistrationStatus.CLAIMED,
            ],
        ).exclude(pk=registration.pk).update(status=TechnicianTelegramRegistrationStatus.SUPERSEDED, updated_at=timezone.now())

        log_audit_event(
            "technician.telegram_registration.link",
            target=f"technician:{technician.id}",
            metadata={
                "registration_id": registration.id,
                "group_chat_id": telegram_group_chat_id,
                "chat_type": telegram_chat_type,
            },
        )
        return Response(
            {
                "detail": "Telegram registration complete.",
                "technician_id": technician.id,
                "registration_status": registration.status,
            }
        )
