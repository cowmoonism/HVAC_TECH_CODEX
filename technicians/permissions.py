from rest_framework import permissions

from accounts.models import UserRole


class TechnicianEndpointPermission(permissions.BasePermission):
    """
    Role gate for the technician directory endpoint.

    Call center users can inspect technician/contact availability for job flow,
    but financial and earnings data should stay out of this API surface.
    """

    write_roles = {
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
    }
    read_roles = write_roles | {
        UserRole.DISPATCHER,
        UserRole.CALL_CENTER,
        UserRole.ACCOUNTANT,
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(getattr(request.user, "profile", None), "role", None)
        if request.method in permissions.SAFE_METHODS:
            return role in self.read_roles
        return role in self.write_roles
