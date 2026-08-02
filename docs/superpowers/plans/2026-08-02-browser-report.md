# Browser Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 공개 저장소 분석을 입력·진행·리포트 상태로 제공하는 단일 FastAPI 웹 화면을 구축한다.

**Architecture:** `web.py` 라우터가 HTML 응답과 정적 asset mount를 제공한다. `app.js`는 기존 분석 API를 호출해 상태를 폴링하고 안전한 DOM API로 리포트를 렌더링한다.

**Tech Stack:** FastAPI, StaticFiles, HTML, CSS, browser JavaScript, pytest.

## Global Constraints

- 기존 `/v1/analyses` API 계약을 변경하지 않는다.
- 사용자·API 응답 텍스트는 `textContent`로만 렌더링한다.
- 첫 릴리스 UI는 `data_engineer` 단일 역할만 노출한다.

### Task 1: 웹 자산과 root 라우트

**Files:** Create `src/proofread/web/index.html`, `src/proofread/web/app.js`, `src/proofread/web/styles.css`, `src/proofread/api/routes/web.py`; modify `src/proofread/api/app.py`; test `tests/api/test_web.py`.

- [ ] Write a failing test that `GET /` returns the analysis form and `app.js` reference.
- [ ] Run `uv run pytest tests/api/test_web.py -v` and confirm route absence.
- [ ] Add root HTML response and static asset mount.
- [ ] Run the test and ruff; commit `feat: add browser analysis form`.

### Task 2: 분석 상태와 리포트 렌더링

**Files:** Modify `src/proofread/web/app.js`, `src/proofread/web/index.html`, `tests/api/test_web.py`.

- [ ] Add a browser-side unit testable renderer contract for queued, running, completed, and failed responses.
- [ ] Implement POST request, 2-second polling, score cards, evidence list, and accessible error state.
- [ ] Run focused and complete tests, lint, Compose config; commit `feat: render browser analysis report`.

## Self-review

The plan covers all design scope: Task 1 renders a safe entry point and Task 2 consumes the existing API through explicit status states. It does not add authentication, a frontend build system, or role expansion.
