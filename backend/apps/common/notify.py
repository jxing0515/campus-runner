"""消息通知：消息以轮询拉取，不做 WebSocket。"""
from apps.common.models import Notification


def notify(user, title, content="", kind=Notification.Kind.BUSINESS, order_no=""):
    if user is None:
        return None
    return Notification.objects.create(user=user, title=title, content=content[:500], kind=kind, order_no=order_no)


def notify_many(users, title, content="", kind=Notification.Kind.BUSINESS):
    return Notification.objects.bulk_create(
        [Notification(user=u, title=title, content=content[:500], kind=kind) for u in users]
    )


def notify_admins(title, content="", super_only=False):
    from apps.accounts.models import User

    qs = User.objects.filter(role=User.Role.ADMIN)
    if super_only:
        qs = qs.filter(admin_level=User.AdminLevel.SUPER)
    return notify_many(list(qs), title, content)
