# riceminer — 커뮤니티 특가 알림 봇

## 1. Objective

한국 커뮤니티 핫딜 게시판을 주기적으로 크롤링해 새 게시글을 Discord 채널에 임베드 형식으로 전송하는 봇.
Discord 슬래시 명령어로 사이트별 크롤링 ON/OFF, 주기 조정을 운영 중 실시간으로 제어한다.

대상 사이트 (3개, 코드명 고정):
| 코드 | 사이트 | URL |
|---|---|---|
| `arca` | 아카라이브 핫딜 | https://arca.live/b/hotdeal |
| `quasarzone` | 퀘이사존 지름/알뜨미 | https://quasarzone.com/bbs/qb_saleinfo |
| `fmkorea` | FM코리아 핫딜 | https://www.fmkorea.com/hotdeal |

## 2. Commands

### 개발/실행
```bash
pip install "scrapling[fetchers]" discord.py python-dotenv
scrapling install              # Scrapling StealthyFetcher(camoufox) 브라우저 의존성
cp .env.example .env           # DISCORD_TOKEN, CHANNEL_ID 채우기
python bot.py                  # 로컬 실행

pytest                         # 테스트 (라이브 크롤링 없음, 저장된 HTML fixture 사용)

docker compose up -d           # 상시 운영 (Dockerfile 없이 Scrapling 공식 이미지 사용)
```

### Discord 슬래시 명령어
| 명령어 | 설명 |
|---|---|
| `/site list` | 활성 사이트(3개)의 상태·주기 조회 |
| `/site on <code>` / `/site off <code>` | 사이트별 크롤링 ON/OFF |
| `/interval set <code> <seconds>` | 사이트별 크롤링 주기 변경 (하한 60초 강제) |
| `/interval get <code>` | 현재 적용 주기 조회 |

명령어 권한은 채널이 속한 서버의 관리자 role로 제한 (`default_member_permissions`).

## 3. Project Structure

```
riceminer/
  bot.py               # 엔트리포인트: 봇 로그인, 슬래시 커맨드 등록, 스케줄러 기동
  scheduler.py          # 사이트별 asyncio 루프, DB에서 interval/enabled를 매 tick 재조회
  db.py                 # sqlite3 (stdlib) 래퍼: sites, seen_posts 테이블
  config.py             # .env 로딩 (DISCORD_TOKEN, CHANNEL_ID, MIN_INTERVAL_SEC)
  crawlers/
    base.py             # Crawler 인터페이스 (fetch → parse → list[Post])
    arca.py
    quasarzone.py
    fmkorea.py
  tests/
    fixtures/*.html     # 사이트별 저장된 샘플 페이지
    test_crawlers.py    # fixture 파싱 검증 (네트워크 호출 없음)
    test_db.py          # in-memory sqlite로 dedup/설정 로직 검증
  docker-compose.yml    # Dockerfile 없이 Scrapling 공식 이미지(pyd4vinci/scrapling) 기반으로 구동
  .env.example
```

- 사이트 추가 시: `crawlers/<code>.py` 1개 파일 + `sites` 테이블 INSERT 1행으로 확장 (새 사이트는 사용자 승인 후에만 추가, boundaries 참조).
- `Post` 데이터클래스(title, url, price, thumbnail, posted_at 등)를 크롤러 공통 반환 타입으로 사용해 Discord embed 변환 로직을 크롤러와 분리.

## 4. Code Style

- Python 3.11+, type hint 필수 (함수 시그니처 기준).
- 포매팅/린트: `ruff` 하나로 통일 (format + lint, 별도 black 불필요).
- 크롤러는 Scrapling의 `StealthyFetcher`(camoufox 기반, 봇 탐지 우회) 사용, 정적으로 충분한 사이트는 가벼운 `Fetcher`로 낮춰 리소스 절약.
- 사이트 HTML 구조 변경에 대비해 Scrapling의 adaptive selector(`adaptive=True`) 사용.
- 비동기 일관성: 봇·스케줄러·크롤러 전부 `asyncio` 기반, 동기 코드 섞지 않음.

## 5. Testing Strategy

- **파서 테스트**: 각 사이트 HTML을 `tests/fixtures/`에 저장해두고 오프라인으로 파싱 검증. 테스트 중 실제 사이트에 요청을 보내지 않는다 (그 자체로 DDoS성 트래픽이 되므로 금지).
- **DB 테스트**: `sqlite3.connect(":memory:")`로 dedup(이미 본 글 재전송 방지), 사이트 on/off, interval 하한 강제 로직 검증.
- **스케줄러 테스트**: 시간 의존 로직은 `unittest.mock`으로 클럭을 mock, 실제 sleep 없이 tick 로직만 검증.
- 신규 크롤러 추가 시 fixture + 파서 테스트 세트 없이는 merge하지 않는다.

## 6. Boundaries

**항상 한다**
- 모든 사이트에 하드 하한 60초 인터벌 강제 (Discord 명령어로도 우회 불가, `config.MIN_INTERVAL_SEC`에서 상수 관리).
- 사이트별 실제 기본 주기는 180초(3분) 권장값으로 시작, 이후 요청 실패율(403/429/캡차)을 관찰하며 운영 중 조정.
- 요청 간 랜덤 지터(jitter) 추가, 동일 IP에서 여러 사이트에 동시 요청 대신 순차 처리.
- 크롤링 실패(403/429/타임아웃)는 예외를 죽이지 않고 로그로 남기고 다음 tick으로 넘어감 (한 사이트 장애가 전체를 멈추지 않게).
- `DISCORD_TOKEN` 등 시크릿은 `.env`로만 관리, 저장소에 커밋 금지 (`.gitignore` 등록).

**먼저 물어본다**
- 활성 3개 사이트 외 신규 대상 사이트 추가.
- `MIN_INTERVAL_SEC` 하한값 자체를 낮추는 변경.
- 배포 환경 변경 (Docker → 다른 방식).
- Discord가 아닌 다른 알림 채널(텔레그램 등) 추가.

**절대 하지 않는다**
- 관리자 명령어로도 하드 하한(60초) 미만으로 크롤링 주기 설정.
- 로그에 `DISCORD_TOKEN`, 쿠키 등 시크릿 출력.
- 로그인 필요 게시판/비공개 컨텐츠 크롤링.
- 병렬로 여러 사이트에 동시다발 요청 (트래픽 패턴이 봇 탐지에 걸리기 쉬움 → 순차 + 지터로 대체).
- 명시적 요청 없이 git tag 생성/push, GitHub Release 생성, Docker 이미지 배포.

## 7. Release & Versioning

jamong-skills MCP(`versioning`, `deploy`)의 규칙을 따른다.

### 버전 형식

```
YY.메이저.마이너   예: 26.1.0
```

| 변경 유형 | 올릴 자리 |
|---|---|
| 새 기능 추가 | 메이저 (마이너는 0으로 초기화) |
| 버그 수정·내부 수정 | 마이너 |
| 연도 변경 | 메이저·마이너 모두 0으로 초기화 |

### CHANGELOG.md

- 버전 정보는 반드시 `CHANGELOG.md`에 기록한다. `[Unreleased]` 섹션은 사용하지 않음 — 작업 완료 시점에 버전을 확정해 바로 기록한다.
- 형식:
  ```markdown
  ## [YY.메이저.마이너] - YYYY-MM-DD

  ### Added
  ### Changed
  ### Fixed
  ### Removed
  ```
  변경 없는 섹션은 생략, 최신 버전이 파일 상단.

### 릴리즈 절차 (명시 요청 시에만)

1. `CHANGELOG.md`에 버전 항목 작성
2. 커밋: `chore: YY.메이저.마이너 릴리즈`
3. `git tag YY.메이저.마이너` → `git push origin YY.메이저.마이너`
4. GitHub Release 생성, 본문은 해당 버전 CHANGELOG 내용 그대로

### Docker 배포

- Watchtower 사용 금지.
- 이미지는 `latest`와 버전 태그(`YY.메이저.마이너`)를 함께 push:
  ```bash
  docker build -t riceminer:latest -t riceminer:YY.메이저.마이너 .
  docker push riceminer:latest && docker push riceminer:YY.메이저.마이너
  ```
- 배포된 컨테이너 갱신은 digest(SHA256) 비교 기반 자동 업데이트로 구성 (`latest` 태그 기준). `diun` 또는 `docker manifest inspect`를 이용한 폴링 스크립트로 감지 후 `docker compose pull && docker compose up -d`.

## 8. 진행 상태 및 다음 단계

**완료**
- `config.py`, `db.py` + `tests/test_db.py`
- `crawlers/base.py` + `arca.py`/`quasarzone.py`/`fmkorea.py` + `tests/test_crawlers.py` (3개 사이트 fixture 기반, 실사이트 라이브 크롤링으로 필드 검증까지 완료)
- `scheduler.py`(순차 방문, 매 tick 재조회, 하한 방어적 재검증, 예외 격리, dedup 후 큐 전달) + `tests/test_scheduler.py`
- `docker-compose.yml`, `.env.example`
- `bot.py`: Discord 로그인, 슬래시 명령어(`/site list|on|off`, `/interval set|get`, 관리자 권한 제한, `SITE_CODES` 검증, `set_interval`의 `ValueError` → 에러 메시지 노출), `format_embed(post: Post) -> discord.Embed` 순수 함수, `scheduler.py`의 `asyncio.Queue`를 소비하는 백그라운드 태스크. `ruff check .` / `python -m pytest` 통과 확인.

**남은 작업**
- **수동 검증 필요(자동화 불가)**: 테스트용 Discord 서버·봇 토큰으로 실제 슬래시 명령어·임베드 전송 확인. 진행 전 준비 여부 확인.

**Phase 6 — 통합 검증 (미착수)**
- `docker compose up -d`로 실제 기동 확인, 로그에 시크릿 노출 없는지 확인 후 `docker compose down`

**보류/결정 필요**
- `Post`에 `price`/`posted_at` 필드 추가 여부 (현재 title/url/thumbnail만 구현)
