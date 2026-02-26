# STEP 04 - RAG and Dockerized Multi-CLI Orchestrator MVP

## 목표

- 프로젝트별 RAG 컨텍스트 주입을 실제 협업 실행 경로에 연결.
- Python Orchestrator에서 Gemini/Codex를 안전하게 디스패치.
- Docker 내부에서 Node/npm 기반 CLI까지 함께 구동되는 복합 런타임 확보.

## MVP 요구사항 반영

1. `parse_spec(file_path)`로 `Task_A/Task_B` 또는 `tasks[]` 파싱.
2. `get_rag_context(query)` 더미 인터페이스(로컬 파일 검색형) 제공.
3. `dispatch_to_cli(agent_type, task, context)`:
   - 리스트 인자 실행(쉘 인젝션 방지)
   - 작업 지시 + RAG 컨텍스트 합성 프롬프트 전달
4. `run_orchestrator()`:
   - 독립 태스크 병렬 실행(`asyncio.gather`)
   - 실패 태스크가 있어도 전체 로그 저장.

## 인증 전략

- 기본: 호스트의 기존 CLI 세션 디렉터리를 컨테이너에 read-only 마운트.
- 보조: 쿠키/토큰 환경변수 주입(`GEMINI_SESSION_COOKIE`, `OPENAI_API_KEY` 등).
- 원칙: 키 하드코딩 금지, `.env`/compose 환경 변수로만 전달.

샘플:

```yaml
volumes:
  - ${HOST_GH_CONFIG_DIR}:/root/.config/gh:ro
  - ${HOST_CODEX_CONFIG_DIR}:/root/.codex:ro
  - ${HOST_GEMINI_CONFIG_DIR}:/root/.config/gemini:ro
```

## 디자인 스펙 샘플

```json
{
  "project": "demo_project",
  "Task_A": {
    "agent_type": "gemini",
    "instruction": "Analyze architecture and produce refactor checklist",
    "rag_query": "docker orchestrator architecture",
    "cwd": "."
  },
  "Task_B": {
    "agent_type": "codex",
    "instruction": "Implement top priority change from checklist",
    "rag_query": "highest priority refactor implementation",
    "cwd": "."
  }
}
```

## 검증 샘플

```bash
docker compose run --rm orchestrator \
  python /app/mvp/orchestrator.py \
  --spec /workspace/orchestrator/mvp/design_spec.example.json \
  --workspace-dir /workspace \
  --rag-dir /workspace \
  --parallel \
  --dry-run
```

기대 결과:

- `failed_count = 0`
- `parallel_executed = true` (독립 태스크일 때)
- run 로그 파일 생성(`/app/data/mvp_runs/*.json`)

## 결과

- 협업형 CLI 실행 경로가 Docker 기반으로 표준화되었고,
- RAG/인증/병렬 실행/실패 로그 저장까지 MVP 요구사항을 충족하는 형태로 정리되었다.
