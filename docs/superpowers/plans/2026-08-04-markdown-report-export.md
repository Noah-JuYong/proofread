# Markdown Report Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 완료된 분석을 전체 진단과 취업 지원 요약 Markdown 파일로 브라우저에서 다운로드한다.

**Architecture:** app.js의 순수 Markdown 변환 함수를 테스트 가능한 별도 모듈로 분리하고, 기존 화면은 두 다운로드 버튼만 연결한다. 모든 처리는 브라우저에서 수행한다.

**Tech Stack:** vanilla JavaScript, pytest, FastAPI static UI, Ruff

## Global Constraints

- 새 API·DB·외부 전송을 추가하지 않는다.
- AI 피드백은 현재 화면에 생성된 경우에만 포함한다.
- 동적 Markdown 텍스트를 이스케이프한다.

### Task 1: Markdown 변환 모듈

**Files:**
- Create: src/proofread/web/report_export.js
- Create: tests/web/test_report_export.mjs

- [ ] Write failing Node tests for full report fields, summary max-three selection, and empty narratives.
- [ ] Run: node --test tests/web/test_report_export.mjs. Expected: module-not-found failure.
- [ ] Implement escapeMarkdown, buildFullReport, buildApplicationSummary, and downloadMarkdown.
- [ ] Run the Node tests again. Expected: pass.
- [ ] Commit: feat: add Markdown report builders.

### Task 2: Browser controls and static contract

**Files:**
- Modify: src/proofread/web/index.html
- Modify: src/proofread/web/app.js
- Modify: tests/api/test_web.py

- [ ] Write failing pytest assertions for two download buttons and report_export.js script.
- [ ] Run: uv run pytest tests/api/test_web.py -v. Expected: failure.
- [ ] Render controls only for completed reports and call downloadMarkdown with the active report and narratives.
- [ ] Run: uv run pytest tests/api/test_web.py -v. Expected: pass.
- [ ] Commit: feat: download Markdown portfolio reports.

### Task 3: Verification and integration

- [ ] Run: uv run pytest -v, uv run ruff check ., docker compose config --quiet, git diff --check.
- [ ] Push branch, open PR for issue #14, wait for checks, squash merge after they pass.

