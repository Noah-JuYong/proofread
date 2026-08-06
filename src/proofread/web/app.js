import { buildApplicationSummary, buildFullReport, downloadMarkdown } from "./report_export.mjs";

const form = document.querySelector("#analysis-form");
const status = document.querySelector("#status");
const report = document.querySelector("#report");
const codexFeedback = document.querySelector("#codex-feedback");
const history = document.querySelector("#history");
const retryAnalysis = document.querySelector("#retry-analysis");
const retryCodex = document.querySelector("#retry-codex");
const downloadError = document.querySelector("#download-error");
const codexBaseUrl = "http://127.0.0.1:8751/v1/codex";
const codexStatusUrl = "http://127.0.0.1:8751/v1/codex/status";
let activeNarratives = [];
let lastAnalysisRequest = null;
let lastAnalysisReport = null;

const categoryLabels = {
  data_flow: "데이터 흐름",
  reproducibility: "재현성",
  quality: "품질",
  operability: "운영성",
  results: "결과",
  infrastructure_as_code: "IaC·클라우드 구성",
  delivery: "컨테이너·배포 자동화",
  platform: "플랫폼·오케스트레이션",
  observability: "관측성·신뢰성",
  security_operations: "보안·운영 문서",
  data_features: "데이터·피처",
  model_development: "모델 개발",
  model_evaluation: "평가·책임 있는 AI",
  experiment_reproducibility: "실험·재현성",
  serving_mlops: "서빙·MLOps",
};

function text(tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  return element;
}

function render(analysis) {
  report.replaceChildren();
  report.hidden = false;
  if (analysis.status !== "completed") {
    status.textContent = analysis.status === "failed"
      ? `분석 실패: ${analysis.error_code}`
      : "분석 중입니다. 잠시만 기다려 주세요.";
    retryAnalysis.hidden = analysis.status !== "failed";
    return;
  }
  retryAnalysis.hidden = true;
  status.textContent = "분석이 완료되었습니다.";
  lastAnalysisReport = analysis.report;
  report.append(text("h2", `총점 ${analysis.report.total_score}/100`));
  const scores = document.createElement("div");
  scores.className = "scores";
  Object.entries(analysis.report.categories).forEach(([name, value]) => {
    const label = categoryLabels[name] ?? name;
    const card = text("div", `${label}: ${value.score}/20`);
    card.className = "score";
    scores.append(card);
  });
  report.append(scores);
  if (analysis.comparison) {
    const delta = analysis.comparison.total_score_delta;
    report.append(text("p", `직전 분석 대비 총점 ${delta >= 0 ? "+" : ""}${delta}점`));
  }
  analysis.report.findings.forEach((finding) => {
    const item = document.createElement("article");
    item.className = "finding";
    item.append(
      text("h3", finding.message),
      text("p", finding.recommendation),
      text("p", finding.evidence.join(" · ")),
    );
    item.lastChild.className = "evidence";
    report.append(item);
  });
  renderCodexFeedback(analysis.report);
  const exports = document.createElement("p");
  exports.append(
    codexButton("전체 Markdown 다운로드", () => safeDownload("proofread-full-report.md", buildFullReport(analysis.report, activeNarratives))),
    codexButton("취업 지원 요약 다운로드", () => safeDownload("proofread-job-application-summary.md", buildApplicationSummary(analysis.report))),
  );
  report.append(exports);
}

function showDownloadError() {
  downloadError.hidden = false;
}

function safeDownload(filename, content) {
  downloadError.hidden = true;
  try { downloadMarkdown(filename, content); } catch { showDownloadError(); }
}

function codexButton(label, callback) {
  const button = text("button", label);
  button.addEventListener("click", callback);
  return button;
}

async function renderCodexFeedback(analysisReport) {
  codexFeedback.replaceChildren();
  codexFeedback.hidden = false;
  try {
    const response = await fetch(codexStatusUrl);
    if (!response.ok) throw new Error("codex_status_failed");
    const status = await response.json();
    retryCodex.hidden = true;
    codexFeedback.append(text("h2", "선택적 Codex AI 피드백"));
    if (!status.authenticated) {
      codexFeedback.append(text("p", "본인 PC의 Codex 계정으로 로그인해 주세요."));
      codexFeedback.append(codexButton("Codex로 로그인", async () => {
        const loginResponse = await fetch(`${codexBaseUrl}/login`, { method: "POST" });
        if (!loginResponse.ok) throw new Error("codex_login_failed");
        await renderCodexFeedback(analysisReport);
      }));
      return;
    }
    codexFeedback.append(codexButton("AI 피드백 생성", async () => {
      const response = await fetch(`${codexBaseUrl}/narratives`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify(analysisReport),
      });
      if (!response.ok) throw new Error("codex_generation_failed");
      const body = await response.json();
      activeNarratives = body.narratives;
      codexFeedback.append(text("p", body.narratives.join(" · ")));
    }));
  } catch {
    codexFeedback.replaceChildren(
      text("h2", "선택적 Codex AI 피드백"),
      text("p", "Codex 연결에 실패했습니다. 로컬 동반 프로세스를 확인해 주세요."),
    );
    retryCodex.hidden = false;
  }
}

async function poll(id) {
  try {
    const response = await fetch(`/v1/analyses/${id}`);
    if (!response.ok) throw new Error("analysis_poll_failed");
    const analysis = await response.json();
    render(analysis);
    if (["queued", "running"].includes(analysis.status)) setTimeout(() => poll(id), 2000);
  } catch {
    status.textContent = "분석 상태를 불러오지 못했습니다.";
    retryAnalysis.hidden = false;
  }
}

async function renderHistory() {
  try {
    const response = await fetch("/v1/analyses");
    const analyses = await response.json();
    history.replaceChildren(text("h2", "최근 분석 이력"));
    analyses.forEach((analysis) => {
      const button = codexButton(`${analysis.repository_url} · ${analysis.status}`, () => poll(analysis.id));
      history.append(button);
    });
  } catch { history.append(text("p", "이력을 불러오지 못했습니다.")); }
}

async function submitAnalysis(request) {
  report.hidden = true;
  retryAnalysis.hidden = true;
  status.textContent = "분석 요청을 전송 중입니다.";
  lastAnalysisRequest = request;
  try {
    const response = await fetch("/v1/analyses", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error("analysis_create_failed");
    poll((await response.json()).analysis_id);
    renderHistory();
  } catch {
    status.textContent = "분석 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.";
    retryAnalysis.hidden = false;
  }
}

function retryLastAnalysis() {
  if (lastAnalysisRequest) submitAnalysis(lastAnalysisRequest);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAnalysis({
    repository_url: document.querySelector("#repository-url").value,
    target_role: document.querySelector("#target-role").value,
  });
});

retryAnalysis.addEventListener("click", retryLastAnalysis);
retryCodex.addEventListener("click", () => {
  if (lastAnalysisReport) renderCodexFeedback(lastAnalysisReport);
});

renderHistory();
