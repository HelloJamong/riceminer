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

# zod는 봇 차단으로 브라우저 기반 크롤링(StealthyFetcher)이 필요해 활성 목록에서 제외
# (crawlers/zod.py 자체는 남아있고 테스트도 통과함 — 필요해지면 여기에 다시 추가)
SITE_CODES = ("arca", "quasarzone", "fmkorea")
