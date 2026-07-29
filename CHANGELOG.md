# Changelog

버전 형식: `YY.메이저.마이너` (예: `26.1.0`). `[Unreleased]` 섹션은 사용하지 않으며, 릴리즈 시점에 버전을 확정해 아래에 항목을 추가한다. 형식·릴리즈 절차는 [SPEC.md](./SPEC.md#7-release--versioning) 참고.

## [26.1.0] - 2026-07-29

### Added
- 커뮤니티 핫딜 크롤러 3종(아카라이브/퀘이사존/FM코리아), sqlite 기반 dedup·사이트 on/off·주기 설정
- Discord 봇: 슬래시 명령어(`/site`, `/interval`, `/channel`), 임베드 알림(사이트명·가격·배송비·썸네일)
- 게시글 전송(post)·에러 로그(log) 채널을 DB(`bot_settings`)에 저장해 봇 추가 후 운영 중 지정 가능
- `Dockerfile` 추가 — 공식 Scrapling 이미지(`pyd4vinci/scrapling`) 위에 riceminer 자체 이미지 빌드

### Changed
- 채널 설정을 `.env` 고정값(`CHANNEL_ID`)에서 `/channel set` 슬래시 명령어 기반으로 전환
- 썸네일을 외부 링크 대신 봇이 다운로드해 첨부파일로 전송 (일부 CDN이 Discord 기본 HTTP 클라이언트를 차단해 임베드가 깨지는 문제 우회)
- `docker-compose.yml`을 공식 이미지 bind mount 방식에서 자체 이미지 빌드(`build: .`) 방식으로 전환

### Fixed
- Guilds 인텐트 누락으로 채널 타입 슬래시 명령어 파라미터가 resolve되지 않던 버그
- 슬래시 명령어 실패 시 무응답으로 보이던 문제 — 전역 에러 핸들러로 사유 응답
