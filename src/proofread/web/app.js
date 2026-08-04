const form = document.querySelector("#analysis-form");
const status = document.querySelector("#status");
const report = document.querySelector("#report");
const codexFeedback = document.querySelector("#codex-feedback");
const codexBaseUrl = "http://127.0.0.1:8751/v1/codex";
const codexStatusUrl = "http://127.0.0.1:8751/v1/codex/status";

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
    return;
  }
  status.textContent = "분석이 완료되었습니다.";
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
    const status = await response.json();
    codexFeedback.append(text("h2", "선택적 Codex AI 피드백"));
    if (!status.authenticated) {
      codexFeedback.append(text("p", "본인 PC의 Codex 계정으로 로그인해 주세요."));
      codexFeedback.append(codexButton("Codex로 로그인", async () => {
        await fetch(`${codexBaseUrl}/login`, { method: "POST" });
        await renderCodexFeedback(analysisReport);
      }));
      return;
    }
    codexFeedback.append(codexButton("AI 피드백 생성", async () => {
      const response = await fetch(`${codexBaseUrl}/narratives`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify(analysisReport),
      });
      const body = await response.json();
      codexFeedback.append(text("p", body.narratives.join(" · ")));
    }));
  } catch {
    codexFeedback.append(text("p", "로컬 AI 기능: uv run proofread-codex-companion"));
  }
}

async function poll(id) {
  const response = await fetch(`/v1/analyses/${id}`);
  const analysis = await response.json();
  render(analysis);
  if (["queued", "running"].includes(analysis.status)) {
    setTimeout(() => poll(id), 2000);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  report.hidden = true;
  status.textContent = "분석 요청을 전송 중입니다.";
  const url = document.querySelector("#repository-url").value;
  const selectedRole = document.querySelector("#target-role").value;
  const response = await fetch("/v1/analyses", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ repository_url: url, target_role: selectedRole }),
  });
  if (!response.ok) {
    status.textContent = "올바른 공개 GitHub 저장소 URL을 입력해 주세요.";
    return;
  }
  poll((await response.json()).analysis_id);
});
