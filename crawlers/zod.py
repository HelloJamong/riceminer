from scrapling.fetchers import StealthyFetcher

from crawlers.base import Crawler, Post


class ZodCrawler(Crawler):
    site_code = "zod"
    list_url = "https://zod.kr/deal"

    async def fetch(self) -> str:
        # zod.kr은 일반 요청은 403으로 차단해 StealthyFetcher(브라우저 기반)가 필요
        response = await StealthyFetcher.async_fetch(self.list_url, headless=True)
        return response.html_content

    def parse(self, html: str) -> list[Post]:
        page = self._page(html)
        container = page.css("ul.zod-board-list--deal")
        rows = container[0].css("li") if container else []
        posts: list[Post] = []
        for row in rows:
            if "notice" in row.attrib.get("class", ""):
                continue
            title_span = row.css("span.app-list-title-item")
            if not title_span:
                continue
            title = str(title_span[0].text).strip()
            if not title:
                continue
            href = None
            for a in row.css("a[href]"):
                h = a.attrib.get("href", "")
                if h.startswith("/deal/"):
                    href = h
                    break
            if not href:
                continue
            thumb_el = row.css("div.app-thumbnail img")
            thumbnail = thumb_el[0].attrib.get("src") if thumb_el else None
            posts.append(
                Post(
                    site=self.site_code,
                    title=title,
                    url=page.urljoin(href),
                    thumbnail=thumbnail,
                )
            )
        return posts
