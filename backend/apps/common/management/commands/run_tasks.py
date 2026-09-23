"""run_tasks：一次性执行定时任务（供系统 cron / schtasks 调用，或测试使用）。"""
from django.core.management.base import BaseCommand

from apps.common import tasks


class Command(BaseCommand):
    help = "执行一轮定时任务；--daily 附带信用恢复/托管告警/对账；--only 指定任务"

    def add_arguments(self, parser):
        parser.add_argument("--daily", action="store_true")
        parser.add_argument("--only", choices=list(tasks.TASKS) + ["recover", "escrow_alert", "reconcile"])

    def handle(self, *args, **options):
        only = options.get("only")
        if only:
            mapping = {**{k: v[0] for k, v in tasks.TASKS.items()}, "recover": tasks.credit_period_recover,
                       "escrow_alert": tasks.escrow_alert, "reconcile": tasks.reconcile}
            result = {only: mapping[only]()}
        else:
            result = tasks.run_all(include_daily=options["daily"])
        self.stdout.write(self.style.SUCCESS(str(result)))
