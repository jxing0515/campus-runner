from django.conf import settings
from django.db import models


class FileAsset(models.Model):
    """文件表：凭证 / 学生证 / 申诉附件统一登记，访问经鉴权接口。"""

    class Kind(models.TextChoices):
        EVIDENCE = "evidence", "凭证"
        STUDENT_CARD = "student_card", "学生证"
        APPEAL = "appeal", "申诉附件"

    file = models.FileField(upload_to="uploads/%Y%m/")
    name = models.CharField(max_length=128)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.EVIDENCE)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="files")
    size = models.PositiveIntegerField(default=0)
    target = models.CharField(max_length=64, blank=True, help_text="关联对象，如 order_no")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class RuleConfig(models.Model):
    """规则配置表：信用 / 超时 / 恢复规则，读取走缓存，修改后删缓存键。"""

    RULE_TYPE = (("credit", "信用"), ("timeout", "超时"), ("recover", "恢复"), ("system", "系统"))

    key = models.CharField(max_length=64, unique=True)
    rule_type = models.CharField(max_length=16, choices=RULE_TYPE, default="credit")
    value = models.CharField(max_length=64)
    description = models.CharField(max_length=200, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}={self.value}"


class Notification(models.Model):
    """通知表：业务消息与公告投递（公告已读即本表已读）。"""

    class Kind(models.TextChoices):
        BUSINESS = "business", "业务"
        ANNOUNCEMENT = "announcement", "公告"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=128)
    content = models.CharField(max_length=500, blank=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.BUSINESS)
    order_no = models.CharField(max_length=32, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]


class Announcement(models.Model):
    """公告表。"""

    title = models.CharField(max_length=128)
    content = models.TextField()
    publisher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="announcements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OperationLog(models.Model):
    """操作日志表：管理员全部写操作审计。"""

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="op_logs"
    )
    module = models.CharField(max_length=32)
    action = models.CharField(max_length=64)
    detail = models.CharField(max_length=500, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["module", "-created_at"])]


def log_action(operator, module, action, detail="", request=None):
    ip = None
    if request is not None:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    return OperationLog.objects.create(operator=operator, module=module, action=action, detail=detail[:500], ip=ip)
