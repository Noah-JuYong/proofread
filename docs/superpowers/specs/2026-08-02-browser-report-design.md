# 브라우저 리포트 설계

## 목표

일반 사용자가 API 도구 없이 공개 GitHub 저장소를 제출하고, Proofread의 근거 기반 분석 리포트를 브라우저에서 읽게 한다.

## 범위

- `GET /`은 URL 입력 폼, 데이터 엔지니어 역할 안내, 분석 시작 버튼을 제공한다.
- 브라우저 JavaScript는 `POST /v1/analyses`를 호출하고 `GET /v1/analyses/{id}`를 2초 간격으로 조회한다.
- `queued`와 `running`에서는 진행 상태를 표시하고, `completed`에서는 총점·다섯 점수·finding·근거 파일 경로를 표시한다.
- `failed`에서는 안전한 오류 코드를 설명하고 재시도를 안내한다.

## 제외 범위

- 로그인, 저장된 리포트 목록, 다중 저장소 비교, 다른 직무 선택
- 별도 JavaScript 번들러·프론트엔드 서버·SPA 프레임워크

## 아키텍처

FastAPI가 HTML, CSS, JavaScript를 정적 파일로 제공한다. 기존 분석 API 계약은 바꾸지 않으며, 브라우저는 그 API의 일반 소비자다. 화면 상태 변환은 브라우저에서만 처리한다.

## 접근성과 안전성

- URL 입력에는 label과 오류 영역을 둔다.
- 진행 상태는 `aria-live`로 알린다.
- API 응답의 텍스트는 HTML 문자열 결합 대신 DOM `textContent`로만 렌더링한다.
- 리포트의 evidence는 텍스트로 표시하고 외부 링크를 자동 생성하지 않는다.

## 검증

- root 페이지가 폼과 정적 자산 링크를 반환하는 API 테스트
- 브라우저 JavaScript의 상태 렌더링과 API 오류 처리 단위 테스트
- 기존 전체 pytest, ruff, Docker Compose 검증
