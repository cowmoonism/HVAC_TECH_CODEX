from rest_framework import serializers

from technicians.models import Technician, TechnicianStatus


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
            queryset = Technician.objects.filter(telegram_user_id=telegram_user_id)
            if instance:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                errors["telegram_user_id"] = "A technician with this Telegram user ID already exists."

        if telegram_group_chat_id:
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
