import os
import sqlite3

os.environ.setdefault("DISCORD_TOKEN", "test_token")
os.environ.setdefault("CHANNEL_ID", "111222333")

import db  # noqa: E402
import config  # noqa: E402


def _memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    db.init_db(conn)
    return conn


def test_seed_creates_all_sites_enabled_with_default_interval():
    conn = _memory_db()
    sites = db.list_sites(conn)
    assert {row["code"] for row in sites} == set(config.SITE_CODES)
    assert all(row["enabled"] == 1 for row in sites)
    assert all(row["interval_sec"] == config.DEFAULT_INTERVAL_SEC for row in sites)


def test_set_enabled_toggles_and_persists():
    conn = _memory_db()
    db.set_enabled(conn, "arca", False)
    assert db.get_site(conn, "arca")["enabled"] == 0
    db.set_enabled(conn, "arca", True)
    assert db.get_site(conn, "arca")["enabled"] == 1


def test_set_interval_rejects_below_floor():
    conn = _memory_db()
    try:
        db.set_interval(conn, "arca", config.MIN_INTERVAL_SEC - 1)
        assert False, "하한 미만 interval이 거부되지 않음"
    except ValueError:
        pass
    assert db.get_site(conn, "arca")["interval_sec"] == config.DEFAULT_INTERVAL_SEC


def test_set_interval_accepts_at_and_above_floor():
    conn = _memory_db()
    db.set_interval(conn, "arca", config.MIN_INTERVAL_SEC)
    assert db.get_site(conn, "arca")["interval_sec"] == config.MIN_INTERVAL_SEC
    db.set_interval(conn, "arca", config.MIN_INTERVAL_SEC + 1)
    assert db.get_site(conn, "arca")["interval_sec"] == config.MIN_INTERVAL_SEC + 1


def test_dedup_round_trip_and_idempotent():
    conn = _memory_db()
    url = "https://arca.live/b/hotdeal/12345"
    assert db.is_seen(conn, "arca", url) is False
    db.mark_seen(conn, "arca", url)
    assert db.is_seen(conn, "arca", url) is True
    db.mark_seen(conn, "arca", url)  # 재호출해도 예외 없이 idempotent
    assert db.is_seen(conn, "arca", url) is True
