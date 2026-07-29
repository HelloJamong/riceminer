import os
from pathlib import Path

os.environ.setdefault("DISCORD_TOKEN", "test_token")

from crawlers.arca import ArcaCrawler  # noqa: E402
from crawlers.quasarzone import QuasarzoneCrawler  # noqa: E402
from crawlers.fmkorea import FmkoreaCrawler  # noqa: E402
from crawlers.base import BlockedError  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


class _FakeResponse:
    def __init__(self, status, html_content=""):
        self.status = status
        self.html_content = html_content


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
    assert any(p.price for p in posts)
    assert any(p.shipping for p in posts)


def test_quasarzone_parses_fixture():
    posts = QuasarzoneCrawler().parse(_fixture("quasarzone.html"))
    _assert_valid_posts(posts, "quasarzone")
    assert any(p.thumbnail for p in posts)
    assert any(p.price for p in posts)
    assert any(p.shipping for p in posts)


def test_fmkorea_parses_fixture():
    posts = FmkoreaCrawler().parse(_fixture("fmkorea.html"))
    _assert_valid_posts(posts, "fmkorea")
    assert any(p.thumbnail for p in posts)
    assert any(p.price for p in posts)
    assert any(p.shipping for p in posts)


def test_check_status_raises_blocked_error_on_non_200():
    try:
        ArcaCrawler()._check_status(_FakeResponse(430))
        assert False, "BlockedError를 발생시켜야 함"
    except BlockedError as exc:
        assert exc.status == 430


def test_check_status_returns_html_on_200():
    html = ArcaCrawler()._check_status(_FakeResponse(200, "<html></html>"))
    assert html == "<html></html>"
