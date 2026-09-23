from django.conf import settings
from django.db import models

from apps.common.models import FileAsset


class Order(models.Model):
    """订单表：需求与订单合一。"""

    class ItemFeeMode(models.TextChoices):
        NONE = "none", "纯跑腿"
        OFFLINE = "offline", "线下付物品费"
        PLATFORM = "platform", "平台代付物品费"

    class Status(models.TextChoices):
        PENDING_PAY = "pending_pay", "待支付"
        PENDING_ACCEPT = "pending_accept", "待接单"
        ACCEPTED = "accepted", "已接单"
        PICKED = "picked", "待取件"
        DELIVERING = "delivering", "配送中"
        PENDING_CONFIRM = "pending_confirm", "待确认"
        COMPLETED = "completed", "已完成"
        CANCELLED = "cancelled", "已取消"
        REFUNDED = "refunded", "已退款"
        APPEALING = "appealing", "申诉中"
        ABNORMAL = "abnormal", "异常"

    class SettleStatus(models.TextChoices):
        NONE = "none", "未结算"
        SETTLED = "settled", "已结算"
        REFUNDED = "refunded", "已退款"
        PARTIAL = "partial", "部分结算/退款"

    order_no = models.CharField(max_length=32, unique=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_orders")
    runner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="runner_orders"
    )
    description = models.CharField(max_length=500)
    pickup_address = models.CharField(max_length=200)
    delivery_address = models.CharField(max_length=200)
    time_window_start = models.DateTimeField()
    time_window_end = models.DateTimeField()
    runner_fee = models.DecimalField(max_digits=10, decimal_places=2)
    item_fee_mode = models.CharField(max_length=16, choices=ItemFeeMode.choices, default=ItemFeeMode.NONE)
    item_fee_estimate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_item_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prepaid = models.BooleanField(default=False, help_text="跑腿员已垫付物品费")
    final_reward = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING_PAY, db_index=True)
    prev_status = models.CharField(max_length=24, blank=True, help_text="占位态进入前的快照")
    settle_status = models.CharField(max_length=16, choices=SettleStatus.choices, default=SettleStatus.NONE)
    cancel_reason = models.CharField(max_length=200, blank=True)
    cancel_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cancelled_orders"
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    accept_at = models.DateTimeField(null=True, blank=True)
    pickup_at = models.DateTimeField(null=True, blank=True)
    deliver_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    auto_confirm_deadline = models.DateTimeField(null=True, blank=True)
    review_deadline = models.DateTimeField(null=True, blank=True)
    no_show_warned_at = models.DateTimeField(null=True, blank=True)
    pickup_file = models.ForeignKey(FileAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    deliver_file = models.ForeignKey(FileAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["student", "status"]),
            models.Index(fields=["runner", "status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_no


class OrderStatusLog(models.Model):
    """订单状态日志表：每次迁移留痕，状态机统一收口。"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    remark = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]


class Review(models.Model):
    """评价表：双向互评，一单每人一条。"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="given_reviews")
    reviewee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="received_reviews")
    score = models.PositiveSmallIntegerField()
    content = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["order", "reviewer"], name="uniq_review_per_order_user")]
        indexes = [models.Index(fields=["reviewee", "-created_at"])]


class Appeal(models.Model):
    """申诉表：争议处理与仲裁资金分配比例。"""

    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        PROCESSING = "processing", "处理中"
        RESOLVED = "resolved", "已裁决"
        REJECTED = "rejected", "已驳回"

    class Winner(models.TextChoices):
        NONE = "none", "未裁决"
        STUDENT = "student", "学生胜诉"
        RUNNER = "runner", "跑腿员胜诉"
        PARTIAL = "partial", "部分责任"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="appeals")
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="appeals")
    respondent = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="appeals_against"
    )
    appeal_type = models.CharField(max_length=32, default="dispute")
    description = models.CharField(max_length=500)
    evidence = models.ForeignKey(FileAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    handler = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    result = models.CharField(max_length=300, blank=True)
    winner = models.CharField(max_length=16, choices=Winner.choices, default=Winner.NONE)
    student_ratio = models.PositiveSmallIntegerField(default=100, help_text="学生获退比例 %，跑腿员得 100-该值")
    deadline = models.DateTimeField(null=True, blank=True)
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
