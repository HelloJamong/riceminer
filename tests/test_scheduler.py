import asyncio
import os
import sqlite3
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DISCORD_TOKEN", "test_token")
os.environ.setdefault("CHANNEL_ID", "111222333")

import config  # noqa: E402
import db  # noqa: E402
from crawlers.base import Post  # noqa: E402
from scheduler import Scheduler, effective_interval  # noqa: E402


class FakeCrawler:
    def __init__(self, site_code, posts=None, error=None, call_log=None):
        self.site_code = site_code
        self._posts = posts or []
        self._error = error
        self.call_count = 0
        self._call_log = call_log

    async def run(self):
        self.call_count += 1
        if self._call_log is not None:
            self._call_log.append(self.site_code)
        if self._error:
            raise self._error
        return list(self._posts)


def _memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    db.init_db(conn)
    return conn


def _make_scheduler(conn, crawlers):
    sched = Scheduler(conn, asyncio.Queue())
    sched.crawlers = crawlers
    return sched


def test_effective_interval_enforces_floor():
    assert effective_interval(10) == config.MIN_INTERVAL_SEC
    assert effective_interval(config.MIN_INTERVAL_SEC) == config.MIN_INTERVAL_SEC
    assert effective_interval(999) == 999


def test_sequential_order_and_skips_disabled():
    conn = _memory_db()
    db.set_enabled(conn, "quasarzone", False)
    call_log: list[str] = []
    crawlers = {
        code: FakeCrawler(code, call_log=call_log) for code in config.SITE_CODES
    }

    async def scenario():
        sched = _make_scheduler(conn, crawlers)
        with patch("scheduler.asyncio.sleep", new=AsyncMock()):
            await sched.tick()

    asyncio.run(scenario())
    # SITE_CODES 고정 순서를 따르되 disabled(quasarzone)는 제외
    assert call_log == [c for c in config.SITE_CODES if c != "quasarzone"]


def test_exception_in_one_site_does_not_abort_cycle():
    conn = _memory_db()
    call_log: list[str] = []
    crawlers = {}
    for code in config.SITE_CODES:
        error = RuntimeError("403") if code == "arca" else None
        crawlers[code] = FakeCrawler(code, error=error, call_log=call_log)

    async def scenario():
        sched = _make_scheduler(conn, crawlers)
        with patch("scheduler.asyncio.sleep", new=AsyncMock()):
            await sched.tick()

    asyncio.run(scenario())
    # arca가 실패해도 나머지 사이트는 같은 tick에서 계속 시도됨
    assert call_log == list(config.SITE_CODES)


def test_new_posts_deduped_and_queued():
    conn = _memory_db()
    post = Post(site="arca", title="특가", url="https://arca.live/b/hotdeal/1", thumbnail=None)
    crawlers = {code: FakeCrawler(code) for code in config.SITE_CODES}
    crawlers["arca"] = FakeCrawler("arca", posts=[post])

    async def scenario():
        sched = _make_scheduler(conn, crawlers)
        with patch("scheduler.asyncio.sleep", new=AsyncMock()):
            await sched.tick()
        items = []
        while not sched.queue.empty():
            items.append(sched.queue.get_nowait())
        return items

    items = asyncio.run(scenario())
    assert items == [post]
    assert db.is_seen(conn, "arca", post.url) is True


def test_floor_respected_across_ticks_even_with_low_db_value():
    conn = _memory_db()
    # set_interval의 검증을 우회해 DB에 직접 하한 미만 값을 심음 (방어 로직 검증 목적)
    conn.execute("UPDATE sites SET interval_sec = 10 WHERE code = 'arca'")
    conn.commit()

    crawlers = {code: FakeCrawler(code) for code in config.SITE_CODES}
    arca = crawlers["arca"]

    async def scenario():
        sched = _make_scheduler(conn, crawlers)
        with patch("scheduler.asyncio.sleep", new=AsyncMock()):
            with patch("scheduler.time.monotonic", return_value=1000.0):
                await sched.tick()  # 최초 tick: 항상 실행됨
            with patch("scheduler.time.monotonic", return_value=1030.0):
                await sched.tick()  # 30초 후: DB엔 10초지만 하한 60초라 아직 스킵돼야 함
            with patch("scheduler.time.monotonic", return_value=1061.0):
                await sched.tick()  # 61초 후: 하한을 넘었으니 다시 실행돼야 함

    asyncio.run(scenario())
    assert arca.call_count == 2
