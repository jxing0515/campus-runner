"""管理员权限位矩阵：operator 与 super_admin 的差异全部收口在此。"""
from rest_framework.permissions import BasePermission

SUPER_ONLY = {"user.ban", "rule.write", "admin.manage", "announce.write"}

OPERATOR_PERMS = {
    "cert.audit",
    "user.view",
    "user.credit",
    "demand.view",
    "order.view",
    "order.resolve",
    "flow.view",
    "escrow.view",
    "settle.view",
    "refund.view",
    "withdraw.audit",
    "appeal.arbitrate",
    "stats.view",
    "announce.view",
    "log.view",
}
SUPER_PERMS = OPERATOR_PERMS | SUPER_ONLY


def has_perm(user, perm):
    if not (user and user.is_authenticated and user.is_admin):
        return False
    return perm in (SUPER_PERMS if user.is_super_admin else OPERATOR_PERMS)


class IsAdmin(BasePermission):
    message = "需要管理员权限"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsSuperAdmin(BasePermission):
    message = "需要超级管理员权限"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_super_admin)


def require_perm(perm):
    """视图按权限位声明：permission_classes = [require_perm("rule.write")]"""

    class _Perm(BasePermission):
        message = f"缺少权限位 {perm}"

        def has_permission(self, request, view):
            return has_perm(request.user, perm)

    _Perm.__name__ = f"Require_{perm.replace('.', '_')}"
    return _Perm
