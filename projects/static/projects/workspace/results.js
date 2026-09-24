import { requestJson, postJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";
import { createStudentLabelResolver } from "./labels.js";
import { bindTabKeys } from "./student-shell.js";

const STATE_LABELS = Object.freeze({ TENSION: "受拉", COMPRESSION: "受压", ZERO: "近似零力", ZERO_FORCE: "近似零力", MIXED: "不同分析段的受力状态不同" });
const COMPARISON_LABELS = Object.freeze({ MATCH: "和预测一致", MISMATCH: "和预测不同", UNSURE: "之前选择“不确定”", NOT_COMPARABLE: "暂不比较" });

export function showComparison(comparison) {
  if (!comparison?.comparison_available) return Object.freeze({ reason: "NO_PREDICTION", text: "这次没有保存预测，因此暂时无法比较。" });
  return (comparison.member_comparisons || []).map((item) => Object.freeze({ clientKey: item.physical_member_client_key, status: item.comparison_status, text: COMPARISON_LABELS[item.comparison_status] || "", actual: item.actual }));
}

export function showExplanation(explanation) {
  return (explanation?.blocks || []).map((block) => Object.freeze({ kind: block.type, clientKey: block.subject?.physical_member_client_key || null, text: block.message_zh_CN?.level_1 || "", segments: block.facts?.segments || [] }));
}

export function focusPhysicalMember(clientKey, focus) {
  return typeof clientKey === "string" ? focus(clientKey) : null;
}

export function showEngineeringDetails(resultJson) {
  const source = resultJson || {};
  return Object.freeze({
    displacements: Array.isArray(source.node_displacements) ? source.node_displacements.map((item) => ({ ...item })) : [],
    reactions: Array.isArray(source.support_reactions) ? source.support_reactions.map((item) => ({ ...item })) : [],
    members: Array.isArray(source.member_results) ? source.member_results.map((item) => ({ ...item })) : [],
    total_mass_g: typeof source.total_mass_g === "number" ? source.total_mass_g : null,
  });
}

export function renderEngineeringDetails(root, details, stale = false) {
  const table = (title, headings, rows) => { const section = document.createElement("section"); const h = document.createElement("h3"); h.textContent = title; section.append(h); const t = document.createElement("table"); const head = document.createElement("tr"); headings.forEach((x) => { const th=document.createElement("th"); th.textContent=x; head.append(th); }); t.append(head); rows.forEach((row) => { const tr=document.createElement("tr"); row.forEach((x) => { const td=document.createElement("td"); td.textContent=x == null ? "—" : String(x); tr.append(td); }); t.append(tr); }); section.append(t); return section; };
  root.replaceChildren(); const note=document.createElement("p"); note.textContent=stale ? "这份工程数据对应较早的模型版本，不能代表当前草稿。请重新分析当前模型，才能得到当前结果。" : "工程详情对应当前模型版本。"; root.append(note);
  root.append(table("节点位移",["分析节点","ux (mm)","uy (mm)"],details.displacements.map((x)=>[x.analysis_node_id,x.ux_mm,x.uy_mm])));
  root.append(table("支座反力",["分析节点","Rx (N)","Ry (N)"],details.reactions.map((x)=>[x.analysis_node_id,x.rx_N,x.ry_N])));
  root.append(table("构件工程数据",["分析段","实体杆件","轴力 (N)","应力 (MPa)","质量 (g)"],details.members.map((x)=>[x.analysis_member_id,x.physical_member_id,x.axial_force_N,x.axial_stress_MPa,x.mass_g])));
  const total=document.createElement("p"); total.textContent=details.total_mass_g === null ? "总质量：—" : `总质量：${details.total_mass_g} g`; root.append(total);
}

function failed(body) {
  const error = normalizeApiError(body);
  const exception = new Error(error.message);
  Object.assign(exception, error);
  return exception;
}

export function showLevelOne(run, data, currentDraftVersion, draft = null) {
  const labels = createStudentLabelResolver(draft || {});
  const segments = (data?.result_json?.member_results || []).flatMap((item) => {
    if (!item?.physical_member_id || !STATE_LABELS[item.state]) return [];
    const member = { physicalMemberClientKey: item.physical_member_id, state: item.state };
    if (draft) member.displayLabel = labels.label("PHYSICAL_MEMBER", item.physical_member_id);
    return [member];
  });
  const states = new Map();
  for (const member of segments) states.set(member.physicalMemberClientKey, [...(states.get(member.physicalMemberClientKey) || []), member.state]);
  const members = [...states].map(([key, values]) => ({
    physicalMemberClientKey: key,
    state: new Set(values).size === 1 ? values[0] : "MIXED",
    ...(draft ? { displayLabel: labels.label("PHYSICAL_MEMBER", key) } : {}),
  }));
  const overlay = Object.fromEntries([...states].map(([key, values]) => [key, new Set(values).size === 1 ? values[0] : "MIXED"]));
  return Object.freeze({
    runId: run.analysis_run_id,
    runNumber: run.runNumber || run.analysis_run_id,
    stale: data.source_draft_version !== currentDraftVersion,
    predictionUsed: run.predictionId !== null,
    maximum: data.level_one?.maximum_displacement ? {
      ...data.level_one.maximum_displacement,
      ...(draft ? { displayCandidateLabels: (data.level_one.maximum_displacement.candidate_analysis_node_ids || []).map((id) => {
        const key = String(id).replace(/^connection:/, "");
        return labels.label("CONNECTION", key);
      }) } : {}),
    } : null,
    members,
    overlay: data.source_draft_version === currentDraftVersion ? overlay : {},
  });
}

export function createResultsWorkspace({ urls, post = postJson, get = requestJson, onChange = () => {} }) {
  let current = { run: null, data: null, predictionId: null };
  const state = () => Object.freeze({ ...current });
  return Object.freeze({
    async analyze(version, predictionId) {
      const bound = Number.isInteger(predictionId) ? predictionId : null;
      const started = await post(urls.analyze, { expected_draft_version: version, prediction_id: bound });
      if (!started.response.ok || !started.body?.ok || started.body.status !== "SUCCESS") throw failed(started.body);
      const data = await get(urlFromTemplate(urls.resultTemplate, { run_id: started.body.analysis_run_id }));
      if (!data.response.ok || !data.body?.ok || data.body.status !== "SUCCESS") throw failed(data.body);
      current = { run: { ...started.body, analysis_run_id: started.body.analysis_run_id, predictionId: bound, source_draft_version: version }, data: data.body, predictionId: bound };
      onChange(state());
      return state();
    },
    async comparison(runId) {
      const result = await get(urlFromTemplate(urls.comparisonTemplate, { run_id: runId }));
      if (!result.response.ok || !result.body?.ok) throw failed(result.body);
      return result.body.comparison;
    },
    async explanation(runId) {
      const result = await get(urlFromTemplate(urls.explanationTemplate, { run_id: runId }));
      if (!result.response.ok || !result.body?.ok) throw failed(result.body);
      return result.body.explanation;
    },
    state,
  });
}

export function renderLevelOne(root, view, focus = () => {}) {
  root.replaceChildren();
  const conclusion = document.createElement("section"); conclusion.dataset.resultConclusion = ""; root.append(conclusion);
  const title = document.createElement("h2"); title.textContent = `第 ${view.runNumber} 次分析 · 结论`; conclusion.append(title);
  const status = document.createElement("p"); status.textContent = view.stale ? "这份分析结果对应较早的模型版本，不能代表当前草稿。请重新分析当前模型，才能得到当前结果。" : "分析已完成，对应当前模型版本。"; conclusion.append(status);
  const prediction = document.createElement("p"); prediction.textContent = view.predictionUsed ? "预测已参与本次分析流程。" : "本次分析未使用预测。"; conclusion.append(prediction);
  const guidance = document.createElement("p"); guidance.textContent = "值得再看：从荷载位置出发，观察相连构件和支座。这里不推断唯一的传力路径。"; conclusion.append(guidance);
  const maximum = document.createElement("p");
  if (view.maximum) {
    const rounded = Number(view.maximum.maximum_displacement_mm).toLocaleString("zh-CN", { maximumFractionDigits: 3 });
    maximum.textContent = `最大位移出现在 ${(view.maximum.displayCandidateLabels || view.maximum.candidate_analysis_node_ids).join("、")}，约为 `;
    const value = document.createElement("strong"); value.dataset.studentRoundedValue = ""; value.textContent = `${rounded} mm`; maximum.append(value, "。");
  } else maximum.textContent = "最大位移结论暂不可用。";
  conclusion.append(maximum);
  const counts = { TENSION: 0, COMPRESSION: 0, ZERO: 0, MIXED: 0 };
  for (const member of view.members) counts[member.state === "ZERO_FORCE" ? "ZERO" : member.state] = (counts[member.state === "ZERO_FORCE" ? "ZERO" : member.state] || 0) + 1;
  const summary = document.createElement("p"); summary.textContent = `受力状态概览：受拉 ${counts.TENSION}；受压 ${counts.COMPRESSION}；近似零力 ${counts.ZERO}；混合状态 ${counts.MIXED}。`; conclusion.append(summary);
  const legend = document.createElement("p"); legend.textContent = "图例：红色实线=受拉；蓝色虚线=受压；灰色点划线=近似零力；紫色分段=混合状态。"; conclusion.append(legend);
  for (const member of view.members) {
    const item = document.createElement("button"); item.type = "button";
    item.dataset.teachingMember = member.physicalMemberClientKey;
    item.textContent = `${member.displayLabel || "构件"}：${STATE_LABELS[member.state]}`;
    item.addEventListener("click", () => focusPhysicalMember(member.physicalMemberClientKey, focus));
    conclusion.append(item);
  }
}

export function renderResultActions(root, { onCompare, onExplain, onTechnical = () => {}, onReport = () => {} }) {
  const actions = document.createElement("div");
  actions.className = "workspace-result-actions"; actions.setAttribute("role", "tablist"); actions.setAttribute("aria-label", "结果内容");
  const select = (name) => {
    root.dataset.uxResultsView = name;
    for (const button of actions.querySelectorAll("button")) {
      const selected = button.dataset.resultView === name;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    }
  };
  for (const [name, text, handler] of [["conclusion", "结论", () => {}], ["compare", "预测对比", onCompare], ["explain", "为什么", onExplain], ["technical", "技术数据", onTechnical]]) {
    const button = document.createElement("button");
    button.type = "button"; button.setAttribute("role", "tab"); button.dataset.resultView = name;
    button.dataset[`result${name[0].toUpperCase()}${name.slice(1)}`] = "";
    button.textContent = text;
    button.addEventListener("click", () => { select(name); handler(); });
    actions.append(button);
  }
  const comparison = document.createElement("section");
  comparison.dataset.resultComparison = "";
  comparison.setAttribute("aria-live", "polite");
  const explanation = document.createElement("section");
  explanation.dataset.resultExplanation = "";
  explanation.setAttribute("aria-live", "polite");
  root.prepend(actions);
  root.append(comparison, explanation);
  bindTabKeys(actions);
  select("conclusion");
}

function appendMixedEvidence(root, item) {
  if (item.actual?.actual_state !== "MIXED") return;
  const explanation = document.createElement("p");
  explanation.textContent = "一根实际构件在分析模型中可能被分成多个分析段，这些分析段的受力状态并不完全相同。";
  const list = document.createElement("ul");
  for (const [index, segment] of (item.actual.segments || []).entries()) {
    const evidence = document.createElement("li");
    const force = Number.isFinite(segment.axial_force_N) ? `，轴力 ${segment.axial_force_N} N` : "";
    evidence.textContent = `分析段 ${index + 1}：${STATE_LABELS[segment.teaching_state] || "状态暂不可用"}${force}。`;
    list.append(evidence);
  }
  root.append(explanation, list);
}

export function renderComparison(root, payload, focus = () => {}, labels = createStudentLabelResolver()) {
  root.replaceChildren();
  const comparison = showComparison(payload);
  if (!Array.isArray(comparison)) {
    const note = document.createElement("p");
    note.textContent = comparison.text;
    root.append(note);
    return;
  }
  for (const item of comparison) {
    const section = document.createElement("section");
    section.dataset.comparisonEvidenceMember = item.clientKey;
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.comparisonMember = item.clientKey;
    button.dataset.teachingMember = item.clientKey;
    button.textContent = `${labels.label("PHYSICAL_MEMBER", item.clientKey)}：${item.text}`;
    button.addEventListener("click", () => focusPhysicalMember(item.clientKey, focus));
    section.append(button);
    appendMixedEvidence(section, item);
    root.append(section);
  }
}

export function renderExplanation(root, payload, focus = () => {}, labels = createStudentLabelResolver()) {
  root.replaceChildren();
  for (const item of showExplanation(payload)) {
    const section = document.createElement("section");
    const block = document.createElement(item.clientKey ? "button" : "p");
    if (item.clientKey) { block.type = "button"; block.dataset.teachingMember = item.clientKey; block.setAttribute("aria-label", `${labels.label("PHYSICAL_MEMBER", item.clientKey)}：${item.text || "结果说明"}`); block.addEventListener("click", () => focusPhysicalMember(item.clientKey, focus)); }
    block.dataset.explanationBlock = "";
    block.textContent = item.kind === "MAXIMUM_DISPLACEMENT" ? "最大位移的位置请查看结论；可观察它与相邻构件的变形关系。" : item.text || "该结果块暂无进一步说明。";
    section.append(block);
    if (item.clientKey && item.segments.length) {
      const list = document.createElement("ul");
      for (const [index, segment] of item.segments.entries()) {
        const line = document.createElement("li");
        const force = Number.isFinite(segment.axial_force_N) ? `，轴力 ${segment.axial_force_N} N` : "";
        line.textContent = `分析段 ${index + 1}：${STATE_LABELS[segment.teaching_state] || "状态暂不可用"}${force}。`;
        list.append(line);
      }
      section.append(list);
    }
    root.append(section);
  }
}
