from rest_framework import permissions

from accounts.models import UserRole


class DashboardPermission(permissions.BasePermission):
    full_access_roles = {
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.DISPATCHER,
    }
    call_center_roles = {UserRole.CALL_CENTER}
    finance_only_roles = {UserRole.ACCOUNTANT}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(getattr(request.user, "profile", None), "role", None)
        endpoint = getattr(view, "dashboard_endpoint", None)

        if role in self.full_access_roles:
            return True
        if role in self.call_center_roles:
            return endpoint in {"overview", "technician_detail", "schedule"}
        if role in self.finance_only_roles:
            return endpoint == "finance_summary"
        return False
