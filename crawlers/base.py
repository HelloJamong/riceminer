from abc import ABC, abstractmethod
from dataclasses import dataclass

from scrapling.parser import Adaptor


@dataclass
class Post:
    site: str
    title: str
    url: str
    thumbnail: str | None


class Crawler(ABC):
    site_code: str
    list_url: str

    @abstractmethod
    async def fetch(self) -> str:
        """목록 페이지 HTML을 가져온다 (네트워크 I/O)."""

    @abstractmethod
    def parse(self, html: str) -> list[Post]:
        """HTML 문자열을 파싱해 Post 목록을 반환한다. 순수 함수 — 네트워크 호출 없음."""

    def _page(self, html: str) -> Adaptor:
        return Adaptor(html, url=self.list_url)

    async def run(self) -> list[Post]:
        html = await self.fetch()
        return self.parse(html)
