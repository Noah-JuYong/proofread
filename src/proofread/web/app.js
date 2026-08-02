const form = document.querySelector("#analysis-form");
const status = document.querySelector("#status");
const report = document.querySelector("#report");

function text(tag, value) { const element = document.createElement(tag); element.textContent = value; return element; }
function render(analysis) {
  report.replaceChildren(); report.hidden = false;
  if (analysis.status !== "completed") { status.textContent = analysis.status === "failed" ? `분석 실패: ${analysis.error_code}` : "분석 중입니다. 잠시만 기다려 주세요."; return; }
  status.textContent = "분석이 완료되었습니다.";
  report.append(text("h2", `총점 ${analysis.report.total_score}/100`));
  const scores = document.createElement("div"); scores.className = "scores";
  Object.entries(analysis.report.categories).forEach(([name, value]) => { const card = text("div", `${name}: ${value.score}/20`); card.className = "score"; scores.append(card); }); report.append(scores);
  analysis.report.findings.forEach((finding) => { const item = document.createElement("article"); item.className = "finding"; item.append(text("h3", finding.message), text("p", finding.recommendation), text("p", finding.evidence.join(" · "))); item.lastChild.className = "evidence"; report.append(item); });
}
async function poll(id) { const response = await fetch(`/v1/analyses/${id}`); const analysis = await response.json(); render(analysis); if (["queued", "running"].includes(analysis.status)) setTimeout(() => poll(id), 2000); }
form.addEventListener("submit", async (event) => { event.preventDefault(); report.hidden = true; status.textContent = "분석 요청을 전송 중입니다."; const url = document.querySelector("#repository-url").value; const response = await fetch("/v1/analyses", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ repository_url: url, target_role: "data_engineer" }) }); if (!response.ok) { status.textContent = "올바른 공개 GitHub 저장소 URL을 입력해 주세요."; return; } poll((await response.json()).analysis_id); });
