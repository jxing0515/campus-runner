from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import FileAsset


class User(AbstractUser):
    """用户表：学生与跑腿员同一账号，跑腿员认证与可提现余额并入本表。"""

    class Role(models.TextChoices):
        USER = "user", "用户"
        ADMIN = "admin", "管理员"

    class AdminLevel(models.TextChoices):
        NONE = "none", "非管理员"
        OPERATOR = "operator", "运营管理员"
        SUPER = "super_admin", "超级管理员"

    class CertStatus(models.TextChoices):
        NONE = "none", "未申请"
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER)
    admin_level = models.CharField(max_length=16, choices=AdminLevel.choices, default=AdminLevel.NONE)
    name = models.CharField(max_length=50, blank=True)
    student_no = models.CharField(max_length=32, blank=True)
    is_runner = models.BooleanField(default=False, help_text="派生字段 =(cert_status==approved)，后端同事务维护")
    runner_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_score = models.IntegerField(default=100)
    banned = models.BooleanField(default=False)
    ban_reason = models.CharField(max_length=200, blank=True)
    cert_status = models.CharField(max_length=16, choices=CertStatus.choices, default=CertStatus.NONE)
    cert_reject_reason = models.CharField(max_length=200, blank=True)
    card_file = models.ForeignKey(FileAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    cert_reviewed_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    cert_reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_count = models.PositiveIntegerField(default=0)
    good_reviews = models.PositiveIntegerField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["role", "banned"]), models.Index(fields=["cert_status"]), models.Index(fields=["student_no"])]

    def __str__(self):
        return self.name or self.username

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_super_admin(self):
        return self.admin_level == self.AdminLevel.SUPER

    @property
    def good_rate(self):
        return round(self.good_reviews / self.review_count, 4) if self.review_count else 0.0

    def sync_runner_flag(self, save=True):
        """认证状态是唯一事实来源，is_runner 与之一致。"""
        self.is_runner = self.cert_status == self.CertStatus.APPROVED
        if save:
            self.save(update_fields=["is_runner", "updated_at"])
        return self.is_runner
