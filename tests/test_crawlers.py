import os
from pathlib import Path

os.environ.setdefault("DISCORD_TOKEN", "test_token")
os.environ.setdefault("CHANNEL_ID", "111222333")

from crawlers.arca import ArcaCrawler  # noqa: E402
from crawlers.quasarzone import QuasarzoneCrawler  # noqa: E402
from crawlers.fmkorea import FmkoreaCrawler  # noqa: E402
from crawlers.zod import ZodCrawler  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _assert_valid_posts(posts, site_code):
    assert len(posts) > 0
    for post in posts:
        assert post.site == site_code
        assert post.title
        assert post.url.startswith("http")


def test_arca_parses_fixture():
    posts = ArcaCrawler().parse(_fixture("arca.html"))
    _assert_valid_posts(posts, "arca")
    assert any(p.thumbnail for p in posts)


def test_quasarzone_parses_fixture():
    posts = QuasarzoneCrawler().parse(_fixture("quasarzone.html"))
    _assert_valid_posts(posts, "quasarzone")
    assert any(p.thumbnail for p in posts)


def test_fmkorea_parses_fixture():
    posts = FmkoreaCrawler().parse(_fixture("fmkorea.html"))
    _assert_valid_posts(posts, "fmkorea")
    assert any(p.thumbnail for p in posts)


def test_zod_parses_fixture():
    posts = ZodCrawler().parse(_fixture("zod.html"))
    _assert_valid_posts(posts, "zod")
    assert any(p.thumbnail for p in posts)
    # 공지/광고 위젯 li는 제외되어야 함
    assert not any("공지" == p.title for p in posts)
