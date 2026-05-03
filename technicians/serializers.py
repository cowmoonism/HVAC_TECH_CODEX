from urllib.parse import quote

from django.conf import settings
from rest_framework import serializers

from technicians.models import (
    Technician,
    TechnicianStatus,
    TechnicianTelegramRegistration,
    TechnicianTelegramRegistrationStatus,
)
from technicians.validators import validate_telegram_numeric


class TechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technician
        fields = (
            "id",
            "first_name",
            "last_name",
            "display_name",
            "phone",
            "email",
            "status",
            "service_state",
            "timezone",
            "telegram_user_id",
            "telegram_username",
            "telegram_group_chat_id",
            "google_calendar_id",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        telegram_user_id = attrs.get(
            "telegram_user_id",
            getattr(instance, "telegram_user_id", ""),
        )
        telegram_group_chat_id = attrs.get(
            "telegram_group_chat_id",
            getattr(instance, "telegram_group_chat_id", ""),
        )
        google_calendar_id = attrs.get(
            "google_calendar_id",
            getattr(instance, "google_calendar_id", ""),
        )
        status = attrs.get("status", getattr(instance, "status", TechnicianStatus.ONBOARDING))

        errors = {}
        if telegram_user_id:
            try:
                validate_telegram_numeric(telegram_user_id, "telegram_user_id")
            except serializers.ValidationError as exc:
                errors["telegram_user_id"] = exc.detail[0] if isinstance(exc.detail, list) else exc.detail
            queryset = Technician.objects.filter(telegram_user_id=telegram_user_id)
            if instance:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                errors["telegram_user_id"] = "A technician with this Telegram user ID already exists."

        if telegram_group_chat_id:
            try:
                validate_telegram_numeric(telegram_group_chat_id, "telegram_group_chat_id")
            except serializers.ValidationError as exc:
                errors["telegram_group_chat_id"] = exc.detail[0] if isinstance(exc.detail, list) else exc.detail
            queryset = Technician.objects.filter(telegram_group_chat_id=telegram_group_chat_id)
            if instance:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                errors["telegram_group_chat_id"] = "A technician with this Telegram group chat ID already exists."

        if status == TechnicianStatus.ACTIVE and not google_calendar_id:
            errors["google_calendar_id"] = "Google Calendar ID is required before a technician can be active."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class TechnicianTelegramRegistrationSerializer(serializers.ModelSerializer):
    bot_start_url = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianTelegramRegistration
        fields = (
            "id",
            "status",
            "token",
            "telegram_user_id",
            "telegram_username",
            "telegram_group_chat_id",
            "telegram_group_title",
            "telegram_chat_type",
            "claimed_at",
            "linked_at",
            "created_at",
            "updated_at",
            "bot_start_url",
        )
        read_only_fields = fields

    def get_bot_start_url(self, obj):
        bot_username = getattr(settings, "TECHNICIAN_BOT_USERNAME", "")
        if not bot_username:
            return ""
        return f"https://t.me/{bot_username}?start={quote(obj.token)}"


def latest_telegram_registration_payload(technician: Technician):
    registration = technician.telegram_registrations.order_by("-created_at").first()
    if registration is None:
        return {
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
    return TechnicianTelegramRegistrationSerializer(registration).data
