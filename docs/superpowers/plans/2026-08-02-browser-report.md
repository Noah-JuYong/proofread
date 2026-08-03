# 브라우저 리포트 구현 계획

> **에이전트 작업자용:** 이 계획을 작업 단위로 구현할 때는 `superpowers:executing-plans` 하위 스킬을 반드시 사용합니다.

**목표:** 공개 저장소 분석을 입력·진행·리포트 상태로 제공하는 단일 FastAPI 웹 화면을 구축한다.

**아키텍처:** `web.py` 라우터가 HTML 응답과 정적 자산 mount를 제공한다. `app.js`는 기존 분석 API를 호출해 상태를 폴링하고 안전한 DOM API로 리포트를 렌더링한다.

**기술 스택:** FastAPI, StaticFiles, HTML, CSS, 브라우저 JavaScript, pytest.

## 공통 제약

- 기존 `/v1/analyses` API 계약을 변경하지 않는다.
- 사용자·API 응답 텍스트는 `textContent`로만 렌더링한다.
- 첫 릴리스 UI는 `data_engineer` 단일 역할만 노출한다.

### 작업 1: 웹 자산과 root 라우트

**파일:** 생성 `src/proofread/web/index.html`, `src/proofread/web/app.js`, `src/proofread/web/styles.css`, `src/proofread/api/routes/web.py`; 수정 `src/proofread/api/app.py`; 테스트 `tests/api/test_web.py`.

- [ ] `GET /`가 분석 폼과 `app.js` 참조를 반환하는 실패 테스트를 작성한다.
- [ ] `uv run pytest tests/api/test_web.py -v`를 실행해 route 부재를 확인한다.
- [ ] root HTML 응답과 정적 자산 mount를 추가한다.
- [ ] 테스트와 ruff를 실행하고 `feat: add browser analysis form`으로 커밋한다.

### 작업 2: 분석 상태와 리포트 렌더링

**파일:** 수정 `src/proofread/web/app.js`, `src/proofread/web/index.html`, `tests/api/test_web.py`.

- [ ] `queued`, `running`, `completed`, `failed` 응답을 위한 브라우저 측 테스트 가능한 renderer 계약을 추가한다.
- [ ] POST 요청, 2초 폴링, 점수 카드, evidence 목록, 접근 가능한 오류 상태를 구현한다.
- [ ] 집중·전체 테스트, lint, Compose config를 실행하고 `feat: render browser analysis report`로 커밋한다.

## 자체 검토

작업 1은 안전한 진입 화면을 렌더링하고, 작업 2는 명시적인 상태 전이를 통해 기존 API를 소비한다. 인증, 프론트엔드 빌드 시스템, 직무 확장은 추가하지 않는다.
