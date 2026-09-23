"""并发控制与限流：缓存 add() 的原子性即分布式锁（DatabaseCache 可跨进程）。"""
import functools
from contextlib import contextmanager

from django.core.cache import cache


@contextmanager
def task_lock(name, timeout=300):
    """定时任务互斥锁：同一任务同一时刻只有一个实例执行。"""
    key = f"lock:{name}"
    acquired = cache.add(key, "1", timeout)
    try:
        yield acquired
    finally:
        if acquired:
            cache.delete(key)


def acquire(name, timeout=30):
    return cache.add(f"lock:{name}", "1", timeout)


def release(name):
    cache.delete(f"lock:{name}")


def rate_limit(key, limit, window=60):
    """固定窗口计数限流，返回 (是否允许, 剩余次数)。"""
    cache_key = f"rl:{key}"
    current = cache.get(cache_key, 0)
    if current >= limit:
        return False, 0
    try:
        current = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, window)
        current = 1
    return True, max(limit - current, 0)


def counter(key):
    return cache.get(key, 0)


def bump(key, window=60):
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        return 1


def clear(key):
    cache.delete(key)


def throttled(key, limit, window=60):
    """视图限流装饰器：超限返回 40001。"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            allowed, _ = rate_limit(key.format(user=request.user.pk if request.user.is_authenticated else "anon"), limit, window)
            if not allowed:
                from apps.common.errors import BizError

                raise BizError("操作过于频繁，请稍后再试", code=40001)
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator
