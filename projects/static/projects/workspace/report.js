import { requestJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

const ISSUE_TEXT = Object.freeze({
  MISSING_MATERIAL_EVIDENCE: "缺少材料资料。", MISSING_MATERIAL_PROPERTY: "材料弹性模量或密度资料不完整。",
  MISSING_SECTION_EVIDENCE: "缺少截面资料。", MISSING_SECTION_PROPERTY: "截面面积资料不完整。",
  MISSING_GEOMETRY_EVIDENCE: "模型几何资料不完整。", MISSING_CONNECTION_EVIDENCE: "显式连接资料不完整。",
  MISSING_SUPPORT_EVIDENCE: "支座资料不完整。", MISSING_LOAD_EVIDENCE: "荷载资料不完整。",
  MISSING_NODE_RESULTS: "节点结果资料不完整。", MISSING_REACTION_RESULTS: "支座反力资料不完整。",
  MISSING_MEMBER_RESULTS: "构件结果资料不完整。", MISSING_DISPLACEMENT_RESULT: "最大位移资料不完整。",
  MISSING_MASS_RESULT: "质量资料不完整。", MISSING_ANALYSIS_MAPPING: "构件分析映射资料不完整。",
});

function failed(body) { const error = normalizeApiError(body); const exception = new Error(error.message); Object.assign(exception, error); return exception; }
function value(item, key) { const result = item?.[key]; return result === null || result === undefined ? "—" : String(result); }
function heading(level, text) { const node = document.createElement(level); node.textContent = text; return node; }
function table(title, headers, rows) { const section = document.createElement("section"); section.append(heading("h3", title)); const node = document.createElement("table"); const tr = document.createElement("tr"); headers.forEach((label) => { const th = document.createElement("th"); th.scope = "col"; th.textContent = label; tr.append(th); }); node.append(tr); rows.forEach((row) => { const line = document.createElement("tr"); row.forEach((cell) => { const td = document.createElement("td"); td.textContent = cell === null || cell === undefined ? "—" : String(cell); line.append(td); }); node.append(line); }); section.append(node); return section; }

export function createReportWorkspace({ urls, get = requestJson }) {
  return Object.freeze({
    async listRuns() { const result = await get(urls.runs); if (!result.response.ok || !result.body?.ok) throw failed(result.body); return result.body.runs || []; },
    async loadReport(runId) { if (!Number.isInteger(runId)) throw Object.assign(new Error("请选择一次分析记录。"), { code: "REPORT_RUN_REQUIRED" }); const result = await get(urlFromTemplate(urls.reportTemplate, { run_id: runId })); if (!result.response.ok || !result.body?.ok) throw failed(result.body); return result.body; },
  });
}

export function renderReport(root, payload, { runNumber = null } = {}) {
  const report = payload?.report || {}; const completeness = payload?.completeness || {}; const provenance = report.provenance || {};
  root.replaceChildren(); root.append(heading("h2", "计算依据 · 计算书资料"));
  const summary = document.createElement("section"); summary.append(heading("h3", runNumber ? `第 ${runNumber} 次分析` : "这次分析"));
  const overall = completeness.overall?.status;
  const status = document.createElement("p"); status.textContent = provenance.is_stale ? "这份资料对应较早一次分析；你的模型后来已经修改。" : overall === "READY" ? "基础工程资料已齐全。" : "还有资料需要补齐。"; summary.append(status);
  const findings = report.results_summary || {};
  const maximumValue = findings.maximum_displacement?.maximum_displacement?.maximum_displacement_mm;
  const maximum = document.createElement("p"); maximum.textContent = `主要结论：最大位移 ${Number.isFinite(maximumValue) ? Number(maximumValue.toFixed(3)) : "—"} mm；总质量 ${value(findings, "total_mass_g")} g。`; summary.append(maximum);
  const assumptionNote = document.createElement("p"); assumptionNote.textContent = "分析假定：二维、线弹性、铰接、构件仅承受轴力。"; summary.append(assumptionNote);
  const issues = Object.values(completeness.blocks || {}).flatMap((block) => block?.status === "MISSING" ? (block.issues || []) : []);
  if (issues.length) { const list = document.createElement("ul"); issues.forEach((issue) => { const item = document.createElement("li"); item.dataset.completenessCode = issue.code; item.textContent = ISSUE_TEXT[issue.code] || "有一项工程资料需要补齐。"; list.append(item); }); summary.append(list); }
  const euler = document.createElement("p"); euler.textContent = "限制：当前版本未提供 Euler 稳定性自动报告；不能作为规范符合性审查或正式工程签字。"; summary.append(euler); root.append(summary);
  const main = document.createElement("details"); main.append(heading("summary", "展开材料、截面、支座、荷载与主要结果"));
  const model = report.geometry_connectivity || {}; main.append(table("模型信息", ["节点", "实体构件", "显式连接"], [[(model.nodes || []).length, (model.physical_members || []).length, (model.connections || []).length]]));
  const materialRows = (report.materials_sections?.materials || []).map((item) => [value(item, "name"), value(item, "E_MPa"), value(item, "density_g_per_mm3")]);
  const sectionRows = (report.materials_sections?.sections || []).map((item) => [value(item, "name"), value(item, "A_mm2"), value(item, "Ix_mm4")]);
  main.append(table("材料", ["材料", "E (MPa)", "密度 (g/mm³)"], materialRows)); main.append(table("截面", ["截面", "A (mm²)", "Ix (mm⁴)"], sectionRows));
  main.append(table("支座与荷载", ["支座", "约束轴", "Fx (N)", "Fy (N)"], [[(report.supports_loads?.supports || []).map((item) => item.support_type).join("、"), (report.supports_loads?.supports || []).map((item) => item.restrained_axis).join("、"), (report.supports_loads?.loads || []).map((item) => value(item, "fx_N")).join("、"), (report.supports_loads?.loads || []).map((item) => value(item, "fy_N")).join("、")]]));
  const assumptions = report.assumptions || {}; main.append(table("分析假定", ["类型", "运动学", "节点", "构件", "单位"], [[value(assumptions, "analysis_type"), value(assumptions, "kinematics"), value(assumptions, "joint_model"), value(assumptions, "member_behavior"), JSON.stringify(assumptions.units || {})]]));
  const results = report.results_summary || {}; main.append(table("主要结果", ["最大位移 (mm)", "总质量 (g)", "受力状态"], [[value(results.maximum_displacement?.maximum_displacement, "maximum_displacement_mm"), value(results, "total_mass_g"), JSON.stringify(results.state_counts || {})]]));
  const limitation = document.createElement("p"); limitation.textContent = "限制说明：当前版本未提供 Euler 稳定性自动报告；本资料不是规范符合性审查或正式工程签字。"; main.append(limitation); root.append(main);
  const details = document.createElement("details"); details.append(heading("summary", "技术明细与追溯信息")); details.append(table("追溯信息", ["AnalysisRun", "Revision", "源草稿", "当前草稿", "Solver"], [[value(provenance, "analysis_run_id"), value(provenance, "model_revision_id"), value(provenance, "source_draft_version"), value(provenance, "current_draft_version"), value(provenance, "solver_version")]]));
  details.append(table("哈希", ["模型 hash", "输入 hash"], [[value(provenance, "model_hash"), value(provenance, "input_hash")]]));
  details.append(table("节点结果", ["节点", "ux (mm)", "uy (mm)"], (report.node_results?.items || []).map((item) => [value(item, "analysis_node_id"), value(item, "ux_mm"), value(item, "uy_mm")])));
  details.append(table("构件结果", ["分析构件", "实体构件", "轴力 (N)", "应力 (MPa)"], (report.member_results?.items || []).map((item) => [value(item, "analysis_member_id"), value(item, "physical_member_id"), value(item, "axial_force_N"), value(item, "axial_stress_MPa")])));
  details.append(table("构件映射", ["实体构件", "分析构件"], Object.entries(model.analysis_member_mapping || {}).map(([physical, analysis]) => [physical, JSON.stringify(analysis)])));
  root.append(details);
  const student = document.createElement("p"); student.textContent = "可在「我的设计说明」记录你的判断。"; root.append(student);
}
