from django.conf import settings
from django.db import models

from apps.orders.models import Order


class PlatformAccount(models.Model):
    """平台账户表（单行汇总账）：托管 = Σ托管中流水。"""

    escrow_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_settled = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_refunded = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def load(cls, for_update=False):
        qs = cls.objects.all()
        if for_update:
            qs = qs.select_for_update()
        account, _ = cls.objects.get_or_create(pk=1)
        if for_update:
            account = cls.objects.select_for_update().get(pk=1)
        return account


class Withdrawal(models.Model):
    """提现记录表：申请即冻结扣减，驳回国滚。"""

    class Status(models.TextChoices):
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    runner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="withdrawals")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    method = models.CharField(max_length=32, default="模拟收款")
    account = models.CharField(max_length=64)
    reject_reason = models.CharField(max_length=200, blank=True)
    flow_no = models.CharField(max_length=32, blank=True)
    handler = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class FundFlow(models.Model):
    """资金流水表：支付/托管/结算/退款/提现扣减/提现退回，幂等键唯一。"""

    class Type(models.TextChoices):
        PAY = "pay", "支付"
        ESCROW = "escrow", "托管"
        SETTLE = "settle", "结算"
        REFUND = "refund", "退款"
        WITHDRAW = "withdraw", "提现扣减"
        WITHDRAW_RETURN = "withdraw_return", "提现退回"

    class Status(models.TextChoices):
        PAID = "paid", "已支付"
        ESCROWED = "escrowed", "托管中"
        SETTLED = "settled", "已结算"
        REFUNDED = "refunded", "已退款"
        FROZEN = "frozen", "已扣减"
        RETURNED = "returned", "已退回"
        PAID_OUT = "paid_out", "已出账"

    class Direction(models.TextChoices):
        IN = "in", "入"
        OUT = "out", "出"

    flow_no = models.CharField(max_length=32, unique=True)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name="flows")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="flows")
    withdrawal = models.ForeignKey(Withdrawal, null=True, blank=True, on_delete=models.PROTECT, related_name="flows")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    direction = models.CharField(max_length=8, choices=Direction.choices)
    type = models.CharField(max_length=20, choices=Type.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    runner_fee_part = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    item_fee_part = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="变动后账户余额快照")
    idem_key = models.CharField(max_length=80, unique=True)
    external_no = models.CharField(max_length=40, blank=True)
    channel = models.CharField(max_length=32, default="平台模拟")
    remark = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["order", "type"]), models.Index(fields=["user", "type"]), models.Index(fields=["-created_at"])]
        ordering = ["-id"]
