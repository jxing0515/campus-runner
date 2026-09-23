"""beat：定时任务调度循环（替代 Celery beat，无 Redis 依赖）。"""
import time
from datetime import datetime

from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.common import rules
from apps.common.tasks import run_all

DAILY_HOUR = 3


class Command(BaseCommand):
    help = "定时任务循环：超时扫描按规则频率执行；每日 03:00 执行信用恢复/托管告警/对账"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=None, help="扫描间隔（秒），默认取规则 scan_interval_seconds")
        parser.add_argument("--once", action="store_true", help="只执行一轮后退出")
        parser.add_argument("--with-daily", action="store_true", help="本轮附带执行每日任务")

    def handle(self, *args, **options):
        interval = options["interval"] or int(rules.get_rule("scan_interval_seconds"))
        self.stdout.write(self.style.SUCCESS(f"beat 启动：扫描间隔 {interval}s"))
        while True:
            include_daily = options["with_daily"]
            today = datetime.now().strftime("%Y%m%d")
            if datetime.now().hour >= DAILY_HOUR and not cache.get(f"daily:{today}"):
                include_daily = True
                cache.set(f"daily:{today}", 1, 86400)
            result = run_all(include_daily=include_daily)
            self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {result}")
            if options["once"]:
                return
            time.sleep(interval)
