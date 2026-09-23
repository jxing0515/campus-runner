"""规则配置读取：DB 为事实来源，Redis/DB 缓存 5 分钟（管理员改规则后删键）。"""
from django.core.cache import cache

CACHE_PREFIX = "rule:"
CACHE_TTL = 300

DEFAULTS = {
    # 信用
    "credit_initial": 100,
    "credit_min": 0,
    "credit_max": 150,
    "credit_delta_complete": 1,
    "credit_delta_good": 2,
    "credit_delta_bad": -5,
    "credit_no_show": -10,
    "review_good_star": 4,
    "review_bad_star": 2,
    # 等级阈值（权限映射）
    "level_excellent": 90,
    "level_good": 80,
    "level_normal": 60,
    # 周期恢复
    "recover_enabled": 1,
    "recover_days": 30,
    "recover_points": 5,
    "recover_target": 100,
    # 超时（分钟）
    "timeout_pay_minutes": 30,
    "timeout_accept_minutes": 60,
    "timeout_confirm_minutes": 1440,
    "timeout_pickup_warn_minutes": 30,
    "timeout_pickup_cancel_minutes": 60,
    "auto_confirm_after_deliver": 1,
    # 其他
    "review_deadline_days": 7,
    "appeal_deadline_hours": 48,
    "escrow_alert_days": 7,
    "scan_interval_seconds": 60,
}

_DESCRIPTIONS = {
    "credit_initial": ("credit", "初始信用分"),
    "credit_min": ("credit", "信用分下限"),
    "credit_max": ("credit", "信用分上限"),
    "credit_delta_complete": ("credit", "订单完成加分"),
    "credit_delta_good": ("credit", "好评加分"),
    "credit_delta_bad": ("credit", "差评扣分"),
    "credit_no_show": ("credit", "爽约扣分"),
    "review_good_star": ("credit", "好评最低星级"),
    "review_bad_star": ("credit", "差评最高星级"),
    "level_excellent": ("credit", "优秀等级阈值（全部权限+可代付）"),
    "level_good": ("credit", "良好等级阈值（全部权限）"),
    "level_normal": ("credit", "一般等级阈值（禁平台代付）"),
    "recover_enabled": ("recover", "启用周期恢复"),
    "recover_days": ("recover", "恢复周期（天）"),
    "recover_points": ("recover", "每周期恢复分数"),
    "recover_target": ("recover", "恢复目标上限"),
    "timeout_pay_minutes": ("timeout", "待支付超时（分钟）"),
    "timeout_accept_minutes": ("timeout", "待接单超时（分钟）"),
    "timeout_confirm_minutes": ("timeout", "待确认超时（分钟）"),
    "timeout_pickup_warn_minutes": ("timeout", "未取件提醒（分钟）"),
    "timeout_pickup_cancel_minutes": ("timeout", "未取件取消（分钟）"),
    "auto_confirm_after_deliver": ("timeout", "有送达凭证才自动确认"),
    "review_deadline_days": ("system", "评价截止天数"),
    "appeal_deadline_hours": ("system", "申诉处理时限（小时）"),
    "escrow_alert_days": ("system", "托管超期告警天数"),
    "scan_interval_seconds": ("system", "扫描间隔（秒）"),
}


def get_rule(key, default=None):
    cached = cache.get(CACHE_PREFIX + key)
    if cached is not None:
        return cached
    from apps.common.models import RuleConfig

    row = RuleConfig.objects.filter(key=key, enabled=True).first()
    if row is None and RuleConfig.objects.filter(key=key).exists():
        value = default if default is not None else DEFAULTS.get(key)
    else:
        value = row.value if row else (default if default is not None else DEFAULTS.get(key))
    if isinstance(value, str) and value.lstrip("-").isdigit():
        value = int(value)
    cache.set(CACHE_PREFIX + key, value, CACHE_TTL)
    return value


def get_rules():
    return {key: get_rule(key, value) for key, value in DEFAULTS.items()}


def set_rule(key, value, rule_type=None, description=""):
    from apps.common.models import RuleConfig

    rule_type = rule_type or _DESCRIPTIONS.get(key, ("system", ""))[0]
    row, _ = RuleConfig.objects.update_or_create(
        key=key, defaults={"value": str(value), "rule_type": rule_type, "description": description}
    )
    cache.delete(CACHE_PREFIX + key)
    return row


def invalidate_rule_cache():
    from apps.common.models import RuleConfig

    keys = [CACHE_PREFIX + k for k in list(DEFAULTS) + list(RuleConfig.objects.values_list("key", flat=True))]
    cache.delete_many(keys)


def ensure_default_rules():
    from apps.common.models import RuleConfig

    for key, value in DEFAULTS.items():
        rule_type, description = _DESCRIPTIONS.get(key, ("system", ""))
        RuleConfig.objects.get_or_create(
            key=key, defaults={"value": str(value), "rule_type": rule_type, "description": description}
        )
