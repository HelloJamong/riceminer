import asyncio
import logging
import random
import sqlite3
import time
from typing import Awaitable, Callable

import config
import db
from crawlers.arca import ArcaCrawler
from crawlers.base import Post
from crawlers.fmkorea import FmkoreaCrawler
from crawlers.quasarzone import QuasarzoneCrawler

logger = logging.getLogger(__name__)

CRAWLERS = {
    "arca": ArcaCrawler,
    "quasarzone": QuasarzoneCrawler,
    "fmkorea": FmkoreaCrawler,
}

JITTER_RANGE_SEC = (1, 5)
POLL_INTERVAL_SEC = 5


def effective_interval(interval_sec: int) -> int:
    """하한 미만 값이 DB에 어떻게든 들어와도 스케줄러가 방어적으로 재검증."""
    return max(interval_sec, config.MIN_INTERVAL_SEC)


class Scheduler:
    def __init__(
        self,
        conn: sqlite3.Connection,
        new_posts_queue: asyncio.Queue[Post],
        poll_interval: int = POLL_INTERVAL_SEC,
        on_error: Callable[[str, str], Awaitable[None]] | None = None,
    ):
        self.conn = conn
        self.queue = new_posts_queue
        self.poll_interval = poll_interval
        self.on_error = on_error
        self.crawlers = {code: cls() for code, cls in CRAWLERS.items()}
        self._last_run: dict[str, float] = {}

    async def run_forever(self) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(self.poll_interval)

    async def tick(self) -> None:
        now = time.monotonic()
        # 사이트를 config.SITE_CODES 고정 순서로 "순차" 방문 — 동시 요청 금지
        for code in config.SITE_CODES:
            site = db.get_site(self.conn, code)
            if site is None or not site["enabled"]:
                continue
            crawler = self.crawlers.get(code)
            if crawler is None:
                continue

            interval = effective_interval(site["interval_sec"])
            last = self._last_run.get(code, 0.0)
            if now - last < interval:
                continue

            try:
                posts = await crawler.run()
            except Exception as exc:
                logger.exception("크롤링 실패: %s", code)
                if self.on_error:
                    try:
                        await self.on_error(code, f"크롤링 실패: {exc}")
                    except Exception:
                        logger.exception("에러 리포트 전송 실패")
                self._last_run[code] = time.monotonic()
                await asyncio.sleep(random.uniform(*JITTER_RANGE_SEC))
                continue

            self._last_run[code] = time.monotonic()
            for post in posts:
                if db.is_seen(self.conn, post.site, post.url):
                    continue
                db.mark_seen(self.conn, post.site, post.url)
                await self.queue.put(post)

            await asyncio.sleep(random.uniform(*JITTER_RANGE_SEC))
