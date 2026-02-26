# 4-Step Consolidated Execution Log

이 문서는 기존 Step 1~20 산출물, strict real-mode 전환, Auth UI 개선, RAG Step 1, Docker 기반 Orchestrator MVP 반영 내역을 **4개의 큰 단계**로 재구성한 인덱스다.

## Index

1. [STEP-01 Architecture Baseline](./STEP-01-architecture-baseline.md)
2. [STEP-02 Workflow and Persistence Core](./STEP-02-workflow-persistence-core.md)
3. [STEP-03 Real Execution and Reliability Hardening](./STEP-03-real-execution-reliability.md)
4. [STEP-04 RAG and Dockerized Multi-CLI Orchestrator MVP](./STEP-04-rag-and-dockerized-mvp.md)

## Why 4 Steps

- 작은 step 로그(1~20)는 추적에는 좋지만 신규 참여자 온보딩 비용이 컸다.
- 4개 큰 축으로 통합해서 "설계 -> 구현 -> 검증 -> 확장" 흐름이 한 번에 보이도록 정리했다.
- 각 문서에 `목표/변경/검증/샘플/다음 액션`을 고정 템플릿으로 넣어 재현성을 높였다.
