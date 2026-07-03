# riceminer

쌀먹을 위한 "쌀 채굴기". 한국 커뮤니티 핫딜 게시판을 캐서 Discord로 실시간 알림을 보내는 봇.

## 기능

- 커뮤니티 핫딜 게시판 크롤링: 아카라이브, 퀘이사존, FM코리아 (Zod는 봇 차단으로 현재 비활성 — `crawlers/zod.py`는 구현·테스트 완료)
- 새 게시글을 Discord 채널에 임베드(제목/썸네일/링크)로 전송
- 슬래시 명령어로 운영 중 실시간 제어
  - `/site on|off <code>`: 사이트별 크롤링 ON/OFF
  - `/site list`: 사이트별 활성 상태·주기 조회
  - `/interval set|get <code> <seconds>`: 사이트별 크롤링 주기 조정
- DDoS 탐지 회피: 하드 하한 60초 인터벌(명령어로도 우회 불가) + 기본 180초 + 랜덤 지터 + 순차 요청

## 기술 스택

| 영역 | 선택 | 이유 |
|---|---|---|
| 언어 | Python 3.11+ | 크롤링·비동기 봇 생태계 성숙 |
| 크롤링 | [Scrapling](https://github.com/D4Vinci/Scrapling) | stealth fetcher(camoufox 기반)로 봇 탐지 우회, adaptive selector로 사이트 구조 변경에 강함 |
| 알림 | Discord Bot (discord.py / py-cord) | 슬래시 명령어로 운영 중 제어 필요 → webhook만으로는 부족 |
| 저장소 | SQLite (stdlib `sqlite3`) | 중복 게시글 방지, 사이트별 on/off·주기 설정 저장. 별도 DB 서버 불필요 |
| 배포 | Docker | 어디서든 동일하게 상시 실행 |
| 테스트 | pytest | 저장된 HTML fixture 기반 오프라인 파싱 검증 (실제 사이트 요청 없음) |
| 린트/포맷 | ruff | 포맷+린트 단일 도구로 통일 |

## 참고 프로젝트

- [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) — 크롤링 엔진으로 직접 사용 (BSD-3-Clause, 고지는 [THIRD_PARTY_LICENSES.md](./THIRD_PARTY_LICENSES.md) 참고)

## 라이선스

MIT License. 자세한 내용은 [LICENSE](./LICENSE) 참고. 서드파티 의존성 라이선스는 [THIRD_PARTY_LICENSES.md](./THIRD_PARTY_LICENSES.md)에 별도 기재.
