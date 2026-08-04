import test from "node:test";
import assert from "node:assert/strict";

import { buildApplicationSummary, buildFullReport } from "../../src/proofread/web/report_export.mjs";

const report = {
  repository_url: "https://github.com/acme/pipeline",
  target_role: "data_engineer",
  total_score: 70,
  categories: {
    data_flow: { score: 20 },
    quality: { score: 15 },
    results: { score: 5 },
  },
  findings: [
    { code: "missing_tests", priority: "high", message: "테스트 부족", recommendation: "테스트 추가", evidence: ["tests/"] },
    { code: "missing_docs", priority: "medium", message: "문서 부족", recommendation: "README 추가", evidence: [] },
  ],
};

test("full report includes score findings and narratives", () => {
  const markdown = buildFullReport(report, ["테스트부터 보강하세요."]);
  assert.match(markdown, /총점: 70\/100/);
  assert.match(markdown, /테스트 부족/);
  assert.match(markdown, /테스트부터 보강하세요/);
});

test("application summary limits strengths and priorities to three", () => {
  const markdown = buildApplicationSummary(report);
  assert.match(markdown, /강점/);
  assert.match(markdown, /우선 개선 과제/);
});
