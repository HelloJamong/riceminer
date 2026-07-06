import asyncio
import logging
import sqlite3

import discord
from discord import app_commands

import config
import db
from crawlers.base import Post
from scheduler import Scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_embed(post: Post) -> discord.Embed:
    embed = discord.Embed(title=post.title, url=post.url)
    if post.thumbnail:
        embed.set_thumbnail(url=post.thumbnail)
    return embed


class RiceminerClient(discord.Client):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__(intents=discord.Intents.none())
        self.conn = conn
        self.tree = app_commands.CommandTree(self)
        self.queue: asyncio.Queue[Post] = asyncio.Queue()
        self.scheduler = Scheduler(conn, self.queue)

    async def setup_hook(self) -> None:
        self.tree.add_command(site_group)
        self.tree.add_command(interval_group)
        await self.tree.sync()
        self.loop.create_task(self.scheduler.run_forever())
        self.loop.create_task(self._consume_queue())

    async def _consume_queue(self) -> None:
        await self.wait_until_ready()
        channel = self.get_channel(config.CHANNEL_ID)
        while True:
            post = await self.queue.get()
            try:
                await channel.send(embed=format_embed(post))
            except Exception:
                logger.exception("임베드 전송 실패: %s", post.url)


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


def main() -> None:
    global client
    conn = sqlite3.connect("riceminer.db")
    db.init_db(conn)
    client = RiceminerClient(conn)
    client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
