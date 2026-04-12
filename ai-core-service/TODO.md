# TODO

## 문서 정리
- [ ] `docs/` 디렉토리 생성 후 CLAUDE.md 상세 내용을 주제별 파일로 분리
  - [ ] `docs/architecture.md` — 서비스 개요, 3단계 체인, 디렉토리 구조
  - [ ] `docs/models.md` — 모델 티어 정의, MODEL_REGISTRY 사용법
  - [ ] `docs/prompts.md` — 프롬프트 버전 관리 (full vs concise)
  - [ ] `docs/experiments.md` — 실험 매트릭스 (EXP-A ~ EXP-F), 실행 방법
  - [ ] `docs/evaluation.md` — 평가 지표, LangSmith, DeepEval
  - [ ] `docs/setup.md` — 로컬 환경 설정, 환경 변수, 실행 명령
  - [ ] `docs/known-issues.md` — 알려진 이슈 및 주의사항
- [ ] CLAUDE.md를 docs/ 파일들을 가리키는 참조 인덱스로 경량화

## 코드 리팩토링
서브 디렉토리부터 순서대로 진행 후 main.py로 마무리

- [ ] `models/` — Pydantic 모델 정리 (Request/Response 스키마 일관성 검토)
- [ ] `load/` — conversation_loader, prompt_loader 인터페이스 통일
- [ ] `config/` — app_config, service_config 역할 분리 명확화 및 중복 제거
- [ ] `utils/` — 유틸 함수 모듈 책임 경계 정리 (계산/파싱/평가 혼재 여부 확인)
- [ ] `services/` — ai_service / chain_ai_service 간 중복 로직 통합
- [ ] `handlers/` — process_handler 청킹·오케스트레이션 로직 가독성 개선
- [ ] `main.py` — 라우터 분리 및 엔드포인트 정리 (최종 단계)

## Claude Skills
- [ ] `auto-push` 스킬 작성
  - 변경 파일 자동 감지 → 스테이징 → 커밋 메시지 생성 → 원격 푸쉬
  - 파일: `.claude/commands/auto-push.md`
- [ ] `review-with-gpt` 스킬 작성 (`/export` 명령어)
  - 현재 진행 계획(플랜 파일)을 Cursor IDE New Agent에 전달할 형태로 export
  - 비평·피드백 수집 후 결과를 대화에 반환
  - 파일: `.claude/commands/export.md`
