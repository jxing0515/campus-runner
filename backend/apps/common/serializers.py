"""输入校验：统一由 DRF Serializer 收口（40001）。"""
from decimal import Decimal

from rest_framework import serializers

from apps.accounts.validators import HasLetterAndDigitValidator
from apps.orders.models import Order


class FlexDateTimeField(serializers.DateTimeField):
    def __init__(self, **kwargs):
        kwargs.setdefault("input_formats", ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "iso-8601"])
        super().__init__(**kwargs)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=32)
    password = serializers.CharField(min_length=8, validators=[HasLetterAndDigitValidator()])
    name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    student_no = serializers.CharField(max_length=32, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=32)
    password = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8, validators=[HasLetterAndDigitValidator()])


class CertificationSerializer(serializers.Serializer):
    student_no = serializers.CharField(max_length=32)
    real_name = serializers.CharField(max_length=50)
    card_file_id = serializers.IntegerField(required=False)


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    kind = serializers.ChoiceField(choices=["evidence", "student_card", "appeal"], default="evidence")
    target = serializers.CharField(max_length=64, required=False, allow_blank=True)


class OrderCreateSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=500)
    pickup_address = serializers.CharField(max_length=200)
    delivery_address = serializers.CharField(max_length=200)
    time_window_start = FlexDateTimeField()
    time_window_end = FlexDateTimeField()
    runner_fee = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    item_fee_mode = serializers.ChoiceField(choices=Order.ItemFeeMode.choices, default=Order.ItemFeeMode.NONE)
    item_fee_estimate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal("0.00"))

    def validate(self, attrs):
        if attrs["item_fee_mode"] == Order.ItemFeeMode.PLATFORM and attrs.get("item_fee_estimate", 0) <= 0:
            raise serializers.ValidationError({"item_fee_estimate": "平台代付需填写物品预估费"})
        return attrs


class PaySerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class ReviewSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    content = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class AppealSerializer(serializers.Serializer):
    appeal_type = serializers.CharField(max_length=32, required=False, default="dispute")
    description = serializers.CharField(max_length=500)
    file_id = serializers.IntegerField(required=False, allow_null=True)


class PickupSerializer(serializers.Serializer):
    file_id = serializers.IntegerField(required=False, allow_null=True)


class DeliverSerializer(serializers.Serializer):
    file_id = serializers.IntegerField(required=False, allow_null=True)
    actual_item_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)


class WithdrawApplySerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.CharField(max_length=32, required=False, default="模拟收款")
    account = serializers.CharField(max_length=64)


class AuditSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class BanSerializer(serializers.Serializer):
    banned = serializers.BooleanField()
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class CreditAdjustSerializer(serializers.Serializer):
    delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class RuleSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    value = serializers.CharField(max_length=64)
    rule_type = serializers.ChoiceField(choices=["credit", "timeout", "recover", "system"], default="system")
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class ArbitrateSerializer(serializers.Serializer):
    winner = serializers.ChoiceField(choices=["student", "runner", "partial"])
    student_ratio = serializers.IntegerField(min_value=0, max_value=100, required=False, allow_null=True)
    remark = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class ResolveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["complete", "cancel"])
    remark = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class AnnouncementSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=128)
    content = serializers.CharField()
