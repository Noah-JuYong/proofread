export function escapeMarkdown(value) {
  return String(value).replaceAll("\\", "\\\\").replaceAll("|", "\\|").replaceAll("\n", " ");
}

export function buildFullReport(report, narratives = []) {
  const lines = ["# Proofread 전체 진단 리포트", "", "- 저장소: " + escapeMarkdown(report.repository_url), "- 지원 직무: " + escapeMarkdown(report.target_role), "- 총점: " + report.total_score + "/100", "", "## 카테고리 점수"];
  for (const [name, value] of Object.entries(report.categories)) lines.push("- " + escapeMarkdown(name) + ": " + value.score + "/20");
  lines.push("", "## 개선 과제");
  for (const finding of report.findings) lines.push("- [" + finding.priority + "] " + escapeMarkdown(finding.message) + " — " + escapeMarkdown(finding.recommendation));
  if (narratives.length) lines.push("", "## AI 피드백", ...narratives.map((item) => "- " + escapeMarkdown(item)));
  return lines.join("\n");
}

export function buildApplicationSummary(report) {
  const strengths = Object.entries(report.categories).sort((a, b) => b[1].score - a[1].score).slice(0, 3);
  const priorities = report.findings.filter((item) => item.priority !== "low").slice(0, 3);
  return ["# Proofread 취업 지원 요약", "", "## 강점", ...strengths.map(([name, value]) => "- " + escapeMarkdown(name) + ": " + value.score + "/20"), "", "## 우선 개선 과제", ...priorities.map((item) => "- " + escapeMarkdown(item.recommendation))].join("\n");
}

export function downloadMarkdown(filename, content) {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(new Blob([content], { type: "text/markdown;charset=utf-8" }));
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}
