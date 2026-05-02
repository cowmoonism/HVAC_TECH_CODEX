from rest_framework import permissions

from accounts.models import UserRole


class ExpenseReportPermission(permissions.BasePermission):
    write_roles = {
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.DISPATCHER,
    }
    read_roles = write_roles | {
        UserRole.ACCOUNTANT,
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if request.method in permissions.SAFE_METHODS:
            return role in self.read_roles
        return role in self.write_roles
