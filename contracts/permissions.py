from rest_framework import permissions

from accounts.models import UserRole


class ServiceContractPermission(permissions.BasePermission):
    full_access_roles = {
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.DISPATCHER,
    }
    call_center_roles = {
        UserRole.CALL_CENTER,
    }
    read_only_roles = {
        UserRole.ACCOUNTANT,
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if role in self.full_access_roles:
            return True
        if role in self.call_center_roles:
            return request.method in {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH"}
        if role in self.read_only_roles:
            return request.method in permissions.SAFE_METHODS
        return False
