import { requestJson, postJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

const STATE_LABELS = Object.freeze({ TENSION: "受拉", COMPRESSION: "受压", ZERO: "零杆", ZERO_FORCE: "零杆" });
const COMPARISON_LABELS = Object.freeze({ MATCH: "预测与分析结果一致。", MISMATCH: "预测与分析结果不同。", UNSURE: "学生原本选择“不确定”。", NOT_COMPARABLE: "当前项目没有可直接比较的结果。" });

export function showComparison(comparison) {
  if (!comparison?.comparison_available) return Object.freeze({ reason: "NO_PREDICTION", text: "本次分析没有绑定已完成 Prediction。" });
  return (comparison.member_comparisons || []).map((item) => Object.freeze({ clientKey: item.physical_member_client_key, status: item.comparison_status, text: COMPARISON_LABELS[item.comparison_status] || "", actual: item.actual }));
}

export function showExplanation(explanation) {
  return (explanation?.blocks || []).map((block) => Object.freeze({ clientKey: block.subject?.physical_member_client_key || null, text: block.message_zh_CN?.level_1 || "", segments: block.facts?.segments || [] }));
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
  root.replaceChildren(); const note=document.createElement("p"); note.textContent=stale ? "当前结果对应较早的模型版本。" : "工程详情对应当前模型版本。"; root.append(note);
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
  const memberLabels = new Map((draft?.physical_members || []).map((member) => {
    const key = member.client_key || member.id;
    return [key, member.label?.trim() || `构件 ${key}`];
  }));
  const connectionLabels = new Map((draft?.connections || []).map((connection) => {
    const key = connection.client_key || connection.id;
    const nodeKey = connection.geometry_node_client_key || connection.geometry_node_id;
    const node = (draft?.nodes || []).find((item) => (item.client_key || item.id) === nodeKey);
    return [key, node?.label?.trim() ? `连接 ${node.label}` : `连接 ${key}`];
  }));
  const members = (data?.result_json?.member_results || []).flatMap((item) => {
    if (!item?.physical_member_id || !STATE_LABELS[item.state]) return [];
    const member = { physicalMemberClientKey: item.physical_member_id, state: item.state };
    if (draft) member.displayLabel = memberLabels.get(item.physical_member_id) || `构件 ${item.physical_member_id}`;
    return [member];
  });
  const states = new Map();
  for (const member of members) states.set(member.physicalMemberClientKey, [...(states.get(member.physicalMemberClientKey) || []), member.state]);
  const overlay = Object.fromEntries([...states].flatMap(([key, values]) => new Set(values).size === 1 ? [[key, values[0]]] : []));
  return Object.freeze({
    runId: run.analysis_run_id,
    stale: data.source_draft_version !== currentDraftVersion,
    predictionUsed: run.predictionId !== null,
    maximum: data.level_one?.maximum_displacement ? {
      ...data.level_one.maximum_displacement,
      ...(draft ? { displayCandidateLabels: (data.level_one.maximum_displacement.candidate_analysis_node_ids || []).map((id) => {
        const key = String(id).replace(/^connection:/, "");
        return connectionLabels.get(key) || `连接 ${key}`;
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

export function renderLevelOne(root, view) {
  root.replaceChildren();
  const title = document.createElement("h2"); title.textContent = `分析结果 · 分析 #${view.runId}`; root.append(title);
  const status = document.createElement("p"); status.textContent = view.stale ? "当前结果对应较早的模型版本。" : "分析已完成，对应当前模型版本。"; root.append(status);
  const prediction = document.createElement("p"); prediction.textContent = view.predictionUsed ? "Prediction 已参与本次分析流程。" : "本次分析未绑定 Prediction。"; root.append(prediction);
  const guidance = document.createElement("p"); guidance.textContent = "观察建议：先看荷载如何进入结构，再看支座如何约束整体运动，最后沿构件观察传力路径；这些提示不替代模型检查。"; root.append(guidance);
  const maximum = document.createElement("p");
  if (view.maximum) {
    const rounded = Number(view.maximum.maximum_displacement_mm).toLocaleString("zh-CN", { maximumFractionDigits: 3 });
    maximum.textContent = `最大位移出现在 ${(view.maximum.displayCandidateLabels || view.maximum.candidate_analysis_node_ids).join("、")}，约为 `;
    const value = document.createElement("strong"); value.dataset.studentRoundedValue = ""; value.textContent = `${rounded} mm`; maximum.append(value, "。");
  } else maximum.textContent = "最大位移结论暂不可用。";
  root.append(maximum);
  const counts = { TENSION: 0, COMPRESSION: 0, ZERO: 0 };
  for (const member of view.members) counts[member.state === "ZERO_FORCE" ? "ZERO" : member.state] = (counts[member.state === "ZERO_FORCE" ? "ZERO" : member.state] || 0) + 1;
  const summary = document.createElement("p"); summary.textContent = `受力状态概览：受拉 ${counts.TENSION}；受压 ${counts.COMPRESSION}；零杆 ${counts.ZERO}。`; root.append(summary);
  const legend = document.createElement("p"); legend.textContent = "图例：实线=受拉；虚线=受压；点划线=零杆。"; root.append(legend);
  for (const member of view.members) { const item = document.createElement("p"); item.textContent = `${member.displayLabel || `构件 ${member.physicalMemberClientKey}`}：${STATE_LABELS[member.state]}`; root.append(item); }
}

export function renderResultActions(root, { onCompare, onExplain, onReport }) {
  const actions = document.createElement("div");
  actions.className = "workspace-result-actions";
  for (const [name, text, handler] of [["compare", "查看预测对比", onCompare], ["explain", "查看结果解释", onExplain], ["report", "查看计算书资料", onReport]]) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset[`result${name[0].toUpperCase()}${name.slice(1)}`] = "";
    button.textContent = text;
    button.addEventListener("click", handler);
    actions.append(button);
  }
  const comparison = document.createElement("section");
  comparison.dataset.resultComparison = "";
  comparison.setAttribute("aria-live", "polite");
  const explanation = document.createElement("section");
  explanation.dataset.resultExplanation = "";
  explanation.setAttribute("aria-live", "polite");
  root.append(actions, comparison, explanation);
}

export function renderComparison(root, payload, focus = () => {}) {
  root.replaceChildren();
  const comparison = showComparison(payload);
  if (!Array.isArray(comparison)) {
    const note = document.createElement("p");
    note.textContent = comparison.text;
    root.append(note);
    return;
  }
  for (const item of comparison) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.comparisonMember = item.clientKey;
    button.textContent = `构件 ${item.clientKey}：${item.text}`;
    button.addEventListener("click", () => focusPhysicalMember(item.clientKey, focus));
    root.append(button);
  }
}

export function renderExplanation(root, payload, focus = () => {}) {
  root.replaceChildren();
  for (const item of showExplanation(payload)) {
    const block = document.createElement(item.clientKey ? "button" : "p");
    if (item.clientKey) { block.type = "button"; block.addEventListener("click", () => focusPhysicalMember(item.clientKey, focus)); }
    block.dataset.explanationBlock = "";
    block.textContent = item.text || "该结果块暂无进一步说明。";
    root.append(block);
  }
}
