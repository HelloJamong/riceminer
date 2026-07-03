from scrapling.fetchers import AsyncFetcher

from crawlers.base import Crawler, Post


class FmkoreaCrawler(Crawler):
    site_code = "fmkorea"
    list_url = "https://www.fmkorea.com/hotdeal"

    async def fetch(self) -> str:
        response = await AsyncFetcher.get(self.list_url)
        return response.html_content

    def parse(self, html: str) -> list[Post]:
        page = self._page(html)
        posts: list[Post] = []
        for row in page.css("li.li"):
            title_a = row.css("h3.title a")
            if not title_a:
                continue
            title_a = title_a[0]
            href = title_a.attrib.get("href")
            if not href:
                continue
            span = title_a.css("span.ellipsis-target")
            title = str(span[0].text).strip() if span else str(title_a.get_all_text()).strip()
            if not title:
                continue
            thumb_el = row.css("img.thumb")
            src = thumb_el[0].attrib.get("data-original") if thumb_el else None
            thumbnail = ("https:" + src) if src and src.startswith("//") else src
            posts.append(
                Post(
                    site=self.site_code,
                    title=title,
                    url=page.urljoin(href),
                    thumbnail=thumbnail,
                )
            )
        return posts
