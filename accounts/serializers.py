from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import UserProfile


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "first_name", "last_name")
        read_only_fields = fields


class AuthUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "role")
        read_only_fields = fields

    def get_role(self, obj):
        profile = getattr(obj, "profile", None)
        return getattr(profile, "role", "")


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        source="user",
        write_only=True,
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user",
            "user_id",
            "role",
            "phone",
            "is_active_staff_member",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")
