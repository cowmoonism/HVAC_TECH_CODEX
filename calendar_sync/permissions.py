from rest_framework import permissions

from accounts.models import UserRole


class CalendarEventPermission(permissions.BasePermission):
    allowed_roles = {
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.DISPATCHER,
        UserRole.CALL_CENTER,
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(getattr(request.user, "profile", None), "role", None)
        return role in self.allowed_roles
