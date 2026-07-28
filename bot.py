import asyncio
import io
import logging
import os
import sqlite3
from urllib.parse import urlsplit

import aiohttp
import discord
from discord import app_commands

import config
import db
from crawlers.base import Post
from scheduler import Scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SITE_NAMES = {
    "arca": "아카라이브",
    "quasarzone": "퀘이사존",
    "fmkorea": "FM코리아",
}

# 일부 이미지 CDN이 Cloudflare 등에서 기본 HTTP 클라이언트 UA를 차단함 — 브라우저처럼 보이도록 지정
THUMBNAIL_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def format_embed(post: Post) -> discord.Embed:
    embed = discord.Embed(title=post.title, url=post.url)
    embed.set_author(name=SITE_NAMES.get(post.site, post.site))
    if post.price:
        embed.add_field(name="가격", value=post.price, inline=True)
    if post.shipping:
        embed.add_field(name="배송비", value=post.shipping, inline=True)
    return embed


async def fetch_thumbnail_file(session: aiohttp.ClientSession, url: str | None) -> discord.File | None:
    """썸네일을 직접 다운받아 첨부파일로 올림 — 일부 CDN이 Discord의 외부 이미지 fetch(HEAD 등)를 막아서 링크만 걸면 안 뜨는 경우가 있음."""
    if not url:
        return None
    parts = urlsplit(url)
    headers = {"User-Agent": THUMBNAIL_USER_AGENT, "Referer": f"{parts.scheme}://{parts.netloc}/"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
    except Exception:
        logger.warning("썸네일 다운로드 실패: %s", url)
        return None
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    return discord.File(io.BytesIO(data), filename=f"thumb{ext}")


class RiceminerClient(discord.Client):
    def __init__(self, conn: sqlite3.Connection):
        # Guilds 인텐트(비특권) 필요: 꺼지면 채널 캐시가 없어 채널 타입 슬래시 명령어 파라미터를 resolve 못 함
        super().__init__(intents=discord.Intents(guilds=True))
        self.conn = conn
        self.tree = app_commands.CommandTree(self)
        self.queue: asyncio.Queue[Post] = asyncio.Queue()
        self.scheduler = Scheduler(conn, self.queue, on_error=self._report_error)
        self._synced_guilds = False

    async def setup_hook(self) -> None:
        self.tree.add_command(site_group)
        self.tree.add_command(interval_group)
        self.tree.add_command(channel_group)
        self.tree.on_error = self._on_command_error
        await self.tree.sync()
        self.loop.create_task(self.scheduler.run_forever())
        self.loop.create_task(self._consume_queue())

    async def on_ready(self) -> None:
        # 글로벌 동기화는 전파에 최대 1시간 걸림 — 가입된 서버엔 즉시 반영되도록 길드 단위로도 동기화
        if not self._synced_guilds:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            self._synced_guilds = True
        logger.info("로그인 완료: %s (길드 %d개 즉시 동기화)", self.user, len(self.guilds))

    async def _on_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.TransformerError):
            message = "채널은 직접 입력하지 말고 자동완성 목록에 뜨는 채널을 선택해주세요."
        else:
            message = f"명령어 처리 중 오류가 발생했습니다: {error}"
        logger.exception("슬래시 명령어 처리 실패", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def _consume_queue(self) -> None:
        await self.wait_until_ready()
        async with aiohttp.ClientSession() as session:
            while True:
                post = await self.queue.get()
                channel_id = db.get_settings(self.conn)["post_channel_id"]
                channel = self.get_channel(channel_id) if channel_id else None
                if channel is None:
                    logger.warning("post 채널 미설정 — 게시글 스킵: %s", post.url)
                    continue
                embed = format_embed(post)
                file = await fetch_thumbnail_file(session, post.thumbnail)
                if file:
                    embed.set_thumbnail(url=f"attachment://{file.filename}")
                try:
                    if file:
                        await channel.send(embed=embed, file=file)
                    else:
                        await channel.send(embed=embed)
                except Exception:
                    logger.exception("임베드 전송 실패: %s", post.url)
                    await self._report_error("discord", f"임베드 전송 실패: {post.url}")

    async def _report_error(self, site_code: str, message: str) -> None:
        channel_id = db.get_settings(self.conn)["log_channel_id"]
        channel = self.get_channel(channel_id) if channel_id else None
        if channel is None:
            return
        try:
            await channel.send(f"⚠️ `{site_code}`: {message}")
        except Exception:
            logger.exception("로그 채널 전송 실패")


client: RiceminerClient


def _validate_site_code(code: str) -> str | None:
    if code not in config.SITE_CODES:
        return f"알 수 없는 사이트 코드: `{code}` (사용 가능: {', '.join(config.SITE_CODES)})"
    return None


site_group = app_commands.Group(
    name="site", description="사이트별 크롤링 ON/OFF", default_permissions=discord.Permissions(administrator=True)
)
interval_group = app_commands.Group(
    name="interval", description="사이트별 크롤링 주기 조정", default_permissions=discord.Permissions(administrator=True)
)
channel_group = app_commands.Group(
    name="channel", description="알림/로그 채널 설정", default_permissions=discord.Permissions(administrator=True)
)


@site_group.command(name="list", description="활성 사이트 상태·주기 조회")
async def site_list(interaction: discord.Interaction) -> None:
    sites = db.list_sites(client.conn)
    lines = [
        f"`{row['code']}`: {'ON' if row['enabled'] else 'OFF'} ({row['interval_sec']}초)"
        for row in sites
    ]
    await interaction.response.send_message("\n".join(lines))


@site_group.command(name="on", description="사이트 크롤링 켜기")
@app_commands.describe(code="사이트 코드")
async def site_on(interaction: discord.Interaction, code: str) -> None:
    if error := _validate_site_code(code):
        await interaction.response.send_message(error, ephemeral=True)
        return
    db.set_enabled(client.conn, code, True)
    await interaction.response.send_message(f"`{code}` 크롤링을 켰습니다.")


@site_group.command(name="off", description="사이트 크롤링 끄기")
@app_commands.describe(code="사이트 코드")
async def site_off(interaction: discord.Interaction, code: str) -> None:
    if error := _validate_site_code(code):
        await interaction.response.send_message(error, ephemeral=True)
        return
    db.set_enabled(client.conn, code, False)
    await interaction.response.send_message(f"`{code}` 크롤링을 껐습니다.")


@interval_group.command(name="set", description="크롤링 주기 변경 (하한 60초)")
@app_commands.describe(code="사이트 코드", seconds="주기(초)")
async def interval_set(interaction: discord.Interaction, code: str, seconds: int) -> None:
    if error := _validate_site_code(code):
        await interaction.response.send_message(error, ephemeral=True)
        return
    try:
        db.set_interval(client.conn, code, seconds)
    except ValueError as e:
        await interaction.response.send_message(str(e), ephemeral=True)
        return
    await interaction.response.send_message(f"`{code}` 주기를 {seconds}초로 설정했습니다.")


@interval_group.command(name="get", description="현재 적용 주기 조회")
@app_commands.describe(code="사이트 코드")
async def interval_get(interaction: discord.Interaction, code: str) -> None:
    if error := _validate_site_code(code):
        await interaction.response.send_message(error, ephemeral=True)
        return
    site = db.get_site(client.conn, code)
    await interaction.response.send_message(f"`{code}` 현재 주기: {site['interval_sec']}초")


@channel_group.command(name="set", description="post(게시글)/log(에러) 채널 지정")
@app_commands.describe(target="post 또는 log", channel="지정할 채널")
@app_commands.choices(
    target=[
        app_commands.Choice(name="post", value="post"),
        app_commands.Choice(name="log", value="log"),
    ]
)
async def channel_set(
    interaction: discord.Interaction, target: app_commands.Choice[str], channel: discord.TextChannel
) -> None:
    if target.value == "post":
        db.set_post_channel(client.conn, channel.id)
    else:
        db.set_log_channel(client.conn, channel.id)
    await interaction.response.send_message(f"{target.value} 채널을 {channel.mention}로 설정했습니다.")


@channel_group.command(name="get", description="현재 지정된 채널 조회")
async def channel_get(interaction: discord.Interaction) -> None:
    settings = db.get_settings(client.conn)
    post = f"<#{settings['post_channel_id']}>" if settings["post_channel_id"] else "미설정"
    log = f"<#{settings['log_channel_id']}>" if settings["log_channel_id"] else "미설정"
    await interaction.response.send_message(f"post: {post}\nlog: {log}")


def main() -> None:
    global client
    conn = sqlite3.connect("riceminer.db")
    db.init_db(conn)
    client = RiceminerClient(conn)
    client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
