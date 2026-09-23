from django.conf import settings
from django.db import models


class CreditLog(models.Model):
    """信用变动表：每次加减分留变动前/后分数与原因码，支持申诉恢复关联。"""

    class Reason(models.TextChoices):
        ORDER_COMPLETE = "order_complete", "订单完成 +1"
        REVIEW_GOOD = "review_good", "好评 +2"
        REVIEW_BAD = "review_bad", "差评 -5"
        NO_SHOW = "no_show", "爽约 -10"
        APPEAL_RESTORE = "appeal_restore", "申诉恢复"
        PERIOD_RECOVER = "period_recover", "周期恢复"
        ADMIN_ADJUST = "admin_adjust", "管理员调整"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credit_logs")
    delta = models.IntegerField()
    score_before = models.IntegerField()
    score_after = models.IntegerField()
    reason_code = models.CharField(max_length=32, choices=Reason.choices)
    rule = models.ForeignKey("common.RuleConfig", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="credit_logs")
    review = models.ForeignKey("orders.Review", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    appeal = models.ForeignKey("orders.Appeal", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    restored = models.BooleanField(default=False, help_text="该次扣分是否已被申诉恢复")
    restore_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="restores")
    remark = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"]), models.Index(fields=["reason_code"])]
        ordering = ["-id"]
