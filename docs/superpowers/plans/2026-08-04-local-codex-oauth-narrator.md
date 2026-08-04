# Local Codex OAuth Narrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자가 자신의 로컬 Codex 로그인으로 규칙 기반 finding의 한국어 개선 피드백을 생성하게 한다.

**Architecture:** Compose 분석 서비스와 분리된 FastAPI 동반 프로세스를 `127.0.0.1:8751`에 실행한다. 동반 프로세스는 Codex CLI의 상태·브라우저 로그인·격리 실행을 제공하며, 브라우저는 완료 리포트를 이 프로세스에 보내 결과 문안만 렌더링한다.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, subprocess, Codex CLI, vanilla JavaScript, pytest, Ruff

## Global Constraints

- OAuth 토큰, Codex 인증 캐시, LLM 요청 본문은 DB·Docker 이미지·로그에 저장하지 않는다.
- 동반 프로세스는 `127.0.0.1`에만 바인딩하고 `http://localhost:8000`, `http://127.0.0.1:8000` Origin만 허용한다.
- LLM 입력은 finding 코드, 우선순위, 근거 목록으로 제한하며 점수·finding 생성은 결정론적 평가기로 유지한다.
- Codex CLI 실행은 프로젝트 파일이 없는 임시 디렉터리와 `read-only` sandbox를 사용한다.
- Codex 미설치·미로그인·실패는 AI 피드백에만 영향을 주며 기존 분석 리포트는 계속 표시한다.

---

## File Structure

| 파일 | 책임 |
| --- | --- |
| `src/proofread/companion/codex.py` | Codex CLI 상태·로그인·격리 서술 실행 경계 |
| `src/proofread/companion/app.py` | localhost 전용 HTTP 계약과 CORS |
| `src/proofread/companion/cli.py` | `proofread-codex-companion` 실행 명령 |
| `tests/companion/test_codex.py` | CLI 어댑터의 입력 제한·실패 동작 |
| `tests/companion/test_app.py` | 상태·로그인·서술·CORS HTTP 계약 |
| `src/proofread/web/*` | 브라우저 로그인·피드백 렌더링 |
| `tests/api/test_web.py` | 브라우저 정적 계약 |
| `pyproject.toml`, `README.md` | 실행 명령과 개인정보 경계 |

### Task 1: Codex CLI 어댑터

**Files:**
- Create: `src/proofread/companion/__init__.py`
- Create: `src/proofread/companion/codex.py`
- Create: `tests/companion/test_codex.py`
- Modify: `src/proofread/llm/narrator.py`

**Interfaces:**
- Consumes: `proofread.llm.client.LlmClient`, `narrate(report, client=codex)`
- Produces: `CodexCli.status() -> CodexStatus`, `CodexCli.start_login() -> None`, `CodexCli.generate(payload: list[dict[str, object]]) -> list[dict[str, str]]`

- [ ] **Step 1: Write the failing CLI tests**

```python
def test_generate_runs_codex_in_read_only_temporary_directory() -> None:
    runner = FakeRunner(stdout='[{"finding_code":"missing_tests","message":"테스트를 추가하세요."}]')
    client = CodexCli(runner=runner)
    client.generate([{"finding_code": "missing_tests", "priority": "high", "evidence": []}])
    assert runner.arguments[:4] == ["codex", "exec", "--sandbox", "read-only"]
    assert "--skip-git-repo-check" in runner.arguments
```

- [ ] **Step 2: Run the test and verify failure**

Run: `uv run pytest tests/companion/test_codex.py -v`

Expected: FAIL because `proofread.companion.codex` does not exist.

- [ ] **Step 3: Implement the smallest CLI boundary**

```python
class CodexCli:
    def status(self) -> CodexStatus:
        return self._runner.login_status()

    def start_login(self) -> None:
        self._runner.start_login()

    def generate(self, payload: list[dict[str, object]]) -> list[dict[str, str]]:
        return self._runner.generate_json(payload)
```

Use `codex login status` return code for authentication and launch `codex login` without reading
or persisting credentials. Run `codex exec --sandbox read-only --skip-git-repo-check` in a
`TemporaryDirectory()`, use a JSON-only prompt, parse a JSON array of string mappings, and raise
typed unavailable, authentication, or generation errors.

- [ ] **Step 4: Add failure and input-boundary tests**

```python
def test_generate_rejects_non_list_json() -> None:
    with pytest.raises(CodexGenerationError):
        CodexCli(runner=FakeRunner(stdout="not json")).generate([])
```

Run: `uv run pytest tests/companion/test_codex.py tests/llm/test_narrator.py -v`

Expected: PASS and narrator payload remains exactly finding code, priority, and evidence.

- [ ] **Step 5: Commit**

```bash
git add src/proofread/companion tests/companion src/proofread/llm/narrator.py
git commit -m "feat: add local Codex CLI narrator"
```

### Task 2: localhost 동반 프로세스 HTTP 계약

**Files:**
- Create: `src/proofread/companion/app.py`
- Create: `tests/companion/test_app.py`

**Interfaces:**
- Consumes: `CodexCli`, `AnalysisReport`, `narrate(report, client=codex)`
- Produces: `create_companion_app(codex: CodexCli | None = None) -> FastAPI`

- [ ] **Step 1: Write the failing API and CORS tests**

```python
async def test_status_reports_authenticated_local_codex() -> None:
    app = create_companion_app(codex=FakeCodex(authenticated=True))
    response = await client.get("/v1/codex/status", headers={"Origin": "http://localhost:8000"})
    assert response.json() == {"available": True, "authenticated": True}

async def test_rejects_an_untrusted_origin() -> None:
    response = await client.options("/v1/codex/status", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in response.headers
```

- [ ] **Step 2: Run the test and verify failure**

Run: `uv run pytest tests/companion/test_app.py -v`

Expected: FAIL because `create_companion_app` does not exist.

- [ ] **Step 3: Implement the narrow companion API**

```python
def create_companion_app(*, codex: CodexCli | None = None) -> FastAPI:
    app = FastAPI(title="Proofread Codex Companion")
    app.state.codex = codex or CodexCli()
    return app

@router.get("/v1/codex/status")
def get_status() -> CodexStatusResponse:
    status = app.state.codex.status()
    return CodexStatusResponse(available=status.available, authenticated=status.authenticated)

@router.post("/v1/codex/login", status_code=202)
def start_login() -> None:
    app.state.codex.start_login()

@router.post("/v1/codex/narratives")
def create_narratives(report: AnalysisReport) -> NarrativeResponse:
    return NarrativeResponse(narratives=narrate(report, client=app.state.codex))
```

Use CORS for the two exact local Origins, no credentials, and only `GET`, `POST`, `OPTIONS`.
Translate unavailable, unauthenticated, and generation errors to stable JSON error codes. Call
`narrate` in the narrative endpoint for the final finding-code validation.

- [ ] **Step 4: Add login and narrative tests**

```python
async def test_login_starts_only_when_codex_is_installed() -> None:
    response = await client.post("/v1/codex/login")
    assert response.status_code == 202
    assert fake_codex.login_started is True

async def test_narratives_return_only_messages_for_report_findings() -> None:
    response = await client.post("/v1/codex/narratives", json=completed_report_json)
    assert response.json()["narratives"] == ["테스트를 추가하세요."]
```

Run: `uv run pytest tests/companion/test_app.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/proofread/companion/app.py tests/companion/test_app.py
git commit -m "feat: expose local Codex companion API"
```

### Task 3: 실행 명령과 문서

**Files:**
- Create: `src/proofread/companion/cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Test: `tests/companion/test_app.py`

**Interfaces:**
- Consumes: `create_companion_app()`
- Produces: `proofread-codex-companion` console script at `127.0.0.1:8751`

- [ ] **Step 1: Write the failing console-script configuration test**

```python
def test_project_declares_local_companion_command() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text())
    assert project["project"]["scripts"]["proofread-codex-companion"] == "proofread.companion.cli:main"
```

- [ ] **Step 2: Run the test and verify failure**

Run: `uv run pytest tests/companion/test_app.py::test_project_declares_local_companion_command -v`

Expected: FAIL because the project has no scripts table.

- [ ] **Step 3: Implement the CLI and exact local workflow documentation**

```python
def main() -> None:
    uvicorn.run(create_companion_app(), host="127.0.0.1", port=8751)
```

Add the script under `[project.scripts]`. Document starting Compose, starting the companion in a
second terminal, selecting `Codex로 로그인`, and generating feedback. State that Docker never
receives OAuth credentials and each user installs and logs in to Codex on their own computer.

- [ ] **Step 4: Run targeted validation**

Run: `uv run pytest tests/companion -v && docker compose config --quiet`

Expected: PASS and no Compose configuration output.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src/proofread/companion/cli.py tests/companion/test_app.py
git commit -m "docs: explain local Codex companion setup"
```

### Task 4: 브라우저 로그인과 AI 피드백 경험

**Files:**
- Modify: `src/proofread/web/index.html`
- Modify: `src/proofread/web/app.js`
- Modify: `src/proofread/web/styles.css`
- Modify: `tests/api/test_web.py`

**Interfaces:**
- Consumes: `GET /v1/codex/status`, `POST /v1/codex/login`, `POST /v1/codex/narratives` at `http://127.0.0.1:8751`
- Produces: `#codex-feedback` area with login, generation, and unavailable states

- [ ] **Step 1: Write the failing browser static-contract test**

```python
def test_root_declares_optional_codex_feedback_controls() -> None:
    assert 'id="codex-feedback"' in response.text
    script = (WEB_DIRECTORY / "app.js").read_text()
    assert "http://127.0.0.1:8751/v1/codex/status" in script
    assert "AI 피드백 생성" in script
```

- [ ] **Step 2: Run the test and verify failure**

Run: `uv run pytest tests/api/test_web.py::test_root_declares_optional_codex_feedback_controls -v`

Expected: FAIL because the UI does not declare Codex controls.

- [ ] **Step 3: Implement browser state transitions**

```javascript
async function refreshCodexFeedback(report) { /* status → login or generate */ }
async function createCodexNarratives(report) { /* render text-only messages */ }
```

Create the feedback section only for completed reports. Use `textContent` for every server-returned
value, disable running buttons, show the local-command hint on connection failure, and render
narratives under matching findings without changing scores or recommendations.

- [ ] **Step 4: Run browser tests**

Run: `uv run pytest tests/api/test_web.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/proofread/web tests/api/test_web.py
git commit -m "feat: add local Codex feedback controls"
```

### Task 5: 전체 검증과 통합 확인

**Files:**
- Modify only if validation finds a scoped defect.

**Interfaces:**
- Consumes: Tasks 1–4
- Produces: 검증된 Compose + 동반 프로세스 로컬 흐름

- [ ] **Step 1: Run the complete automated suite**

Run: `uv run pytest -v && uv run ruff check . && docker compose config --quiet && git diff --check`

Expected: all tests pass, Ruff reports no violations, Compose validates, and the diff is clean.

- [ ] **Step 2: Run a real non-authentication smoke check**

Run: `uv run proofread-codex-companion` and `curl http://127.0.0.1:8751/v1/codex/status`

Expected: JSON status only. Do not print credentials or start a login flow.

- [ ] **Step 3: Commit only a scoped correction when required**

```bash
git add <corrected-files>
git commit -m "fix: correct local Codex companion verification"
```

Skip this commit when no correction was needed.
