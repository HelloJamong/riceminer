import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} 환경변수가 설정되지 않았습니다 (.env 확인)")
    return value


DISCORD_TOKEN: str = _require("DISCORD_TOKEN")
CHANNEL_ID: int = int(_require("CHANNEL_ID"))

# 하한/기본 크롤링 주기는 DDoS 탐지 회피를 위한 하드 상수 — .env로 우회 불가
MIN_INTERVAL_SEC = 60
DEFAULT_INTERVAL_SEC = 180

SITE_CODES = ("arca", "quasarzone", "fmkorea")
