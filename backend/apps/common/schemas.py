"""输出序列化：统一金额为两位小数字符串，避免 float。"""
from apps.credit import services as credit_services


def s(value):
    return None if value is None else f"{value:.2f}"


def dt(value):
    if not value:
        return None
    from django.utils import timezone

    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")


def user_dict(user, with_limits=False):
    from apps.credit import services as credit_services

    data = {
        "id": user.id,
        "username": user.username,
        "name": user.name or user.username,
        "role": user.role,
        "admin_level": user.admin_level,
        "student_no": user.student_no,
        "is_runner": user.is_runner,
        "cert_status": user.cert_status,
        "cert_reject_reason": user.cert_reject_reason,
        "credit_score": user.credit_score,
        "credit_level": credit_services.level_of(user.credit_score),
        "runner_balance": s(user.runner_balance),
        "banned": user.banned,
        "ban_reason": user.ban_reason,
        "completed_count": user.completed_count,
        "good_rate": user.good_rate,
        "created_at": dt(user.created_at),
    }
    if with_limits:
        data["limits"] = credit_services.limits_of(user)
    return data


def file_dict(asset):
    return {"id": asset.id, "name": asset.name, "kind": asset.kind, "size": asset.size, "url": f"/api/v1/files/{asset.id}"}


def order_dict(order, detail=False):
    from apps.orders import state

    student_ok, runner_ok, note = state.cancel_policy(order)
    data = {
        "order_no": order.order_no,
        "status": order.status,
        "status_label": order.get_status_display(),
        "prev_status": order.prev_status,
        "student": {"id": order.student_id, "name": order.student.name or order.student.username},
        "runner": {"id": order.runner_id, "name": (order.runner.name or order.runner.username) if order.runner_id else None},
        "description": order.description,
        "pickup_address": order.pickup_address,
        "delivery_address": order.delivery_address,
        "time_window_start": dt(order.time_window_start),
        "time_window_end": dt(order.time_window_end),
        "runner_fee": s(order.runner_fee),
        "item_fee_mode": order.item_fee_mode,
        "item_fee_estimate": s(order.item_fee_estimate),
        "actual_item_fee": s(order.actual_item_fee),
        "prepaid": order.prepaid,
        "final_reward": s(order.final_reward),
        "settle_status": order.settle_status,
        "cancel_reason": order.cancel_reason,
        "paid_at": dt(order.paid_at),
        "accept_at": dt(order.accept_at),
        "pickup_at": dt(order.pickup_at),
        "deliver_at": dt(order.deliver_at),
        "completed_at": dt(order.completed_at),
        "auto_confirm_deadline": dt(order.auto_confirm_deadline),
        "review_deadline": dt(order.review_deadline),
        "pickup_file": order.pickup_file_id,
        "deliver_file": order.deliver_file_id,
        "created_at": dt(order.created_at),
        "can_cancel_by_student": student_ok,
        "can_cancel_by_runner": runner_ok,
        "cancel_note": note,
        "reviewed_by": list(order.reviews.values_list("reviewer_id", flat=True)),
    }
    if detail:
        data["status_logs"] = [
            {
                "from": log.from_status,
                "to": log.to_status,
                "operator": log.operator.name if log.operator else "系统",
                "remark": log.remark,
                "created_at": dt(log.created_at),
            }
            for log in order.status_logs.select_related("operator")
        ]
        data["reviews"] = [review_dict(r) for r in order.reviews.select_related("reviewer", "reviewee")]
        data["appeals"] = [appeal_dict(a) for a in order.appeals.all()]
        data["flows"] = [flow_dict(f) for f in order.flows.all()[:50]]
    return data


def review_dict(review):
    return {
        "id": review.id,
        "order_no": review.order_id and review.order.order_no,
        "reviewer": {"id": review.reviewer_id, "name": review.reviewer.name or review.reviewer.username},
        "reviewee": {"id": review.reviewee_id, "name": review.reviewee.name or review.reviewee.username},
        "score": review.score,
        "content": review.content,
        "created_at": dt(review.created_at),
    }


def appeal_dict(appeal):
    return {
        "id": appeal.id,
        "order_no": appeal.order.order_no,
        "initiator": {"id": appeal.initiator_id, "name": appeal.initiator.name or appeal.initiator.username},
        "respondent": {"id": appeal.respondent_id, "name": (appeal.respondent.name or appeal.respondent.username) if appeal.respondent_id else None},
        "appeal_type": appeal.appeal_type,
        "description": appeal.description,
        "evidence": appeal.evidence_id,
        "status": appeal.status,
        "status_label": appeal.get_status_display(),
        "winner": appeal.winner,
        "student_ratio": appeal.student_ratio,
        "result": appeal.result,
        "handler": appeal.handler.name if appeal.handler_id else None,
        "deadline": dt(appeal.deadline),
        "handled_at": dt(appeal.handled_at),
        "created_at": dt(appeal.created_at),
    }


def flow_dict(flow):
    return {
        "flow_no": flow.flow_no,
        "order_no": flow.order.order_no if flow.order_id else None,
        "withdrawal_id": flow.withdrawal_id,
        "user": {"id": flow.user_id, "name": (flow.user.name or flow.user.username) if flow.user_id else None},
        "amount": s(flow.amount),
        "direction": flow.direction,
        "type": flow.type,
        "type_label": flow.get_type_display(),
        "status": flow.status,
        "status_label": flow.get_status_display(),
        "runner_fee_part": s(flow.runner_fee_part),
        "item_fee_part": s(flow.item_fee_part),
        "balance_after": s(flow.balance_after),
        "external_no": flow.external_no,
        "channel": flow.channel,
        "remark": flow.remark,
        "created_at": dt(flow.created_at),
    }


def withdrawal_dict(wd):
    return {
        "id": wd.id,
        "runner": {"id": wd.runner_id, "name": wd.runner.name or wd.runner.username},
        "amount": s(wd.amount),
        "balance_before": s(wd.balance_before),
        "balance_after": s(wd.balance_after),
        "status": wd.status,
        "status_label": wd.get_status_display(),
        "method": wd.method,
        "account": wd.account,
        "reject_reason": wd.reject_reason,
        "flow_no": wd.flow_no,
        "handler": wd.handler.name if wd.handler_id else None,
        "handled_at": dt(wd.handled_at),
        "created_at": dt(wd.created_at),
    }


def credit_log_dict(log):
    return {
        "id": log.id,
        "delta": log.delta,
        "score_before": log.score_before,
        "score_after": log.score_after,
        "reason_code": log.reason_code,
        "reason_label": log.get_reason_code_display(),
        "order_no": log.order.order_no if log.order_id else None,
        "remark": log.remark,
        "restored": log.restored,
        "restore_of": log.restore_of_id,
        "created_at": dt(log.created_at),
    }


def notification_dict(item):
    return {
        "id": item.id,
        "title": item.title,
        "content": item.content,
        "kind": item.kind,
        "order_no": item.order_no,
        "is_read": item.is_read,
        "created_at": dt(item.created_at),
    }


def rule_dict(rule):
    return {
        "id": rule.id,
        "key": rule.key,
        "name": rule.description or rule.key,
        "rule_type": rule.rule_type,
        "value": rule.value,
        "description": rule.description,
        "enabled": rule.enabled,
        "updated_at": dt(rule.updated_at),
    }


def log_dict(log):
    return {
        "id": log.id,
        "operator": (log.operator.name or log.operator.username) if log.operator_id else "系统",
        "module": log.module,
        "action": log.action,
        "detail": log.detail,
        "ip": log.ip,
        "created_at": dt(log.created_at),
    }


def credit_limits(user):
    return credit_services.limits_of(user)
