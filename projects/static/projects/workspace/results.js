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

export function showLevelOne(run, data, currentDraftVersion) {
  const members = (data?.result_json?.member_results || []).flatMap((item) => {
    if (!item?.physical_member_id || !STATE_LABELS[item.state]) return [];
    return [{ physicalMemberClientKey: item.physical_member_id, state: item.state }];
  });
  const states = new Map();
  for (const member of members) states.set(member.physicalMemberClientKey, [...(states.get(member.physicalMemberClientKey) || []), member.state]);
  const overlay = Object.fromEntries([...states].flatMap(([key, values]) => new Set(values).size === 1 ? [[key, values[0]]] : []));
  return Object.freeze({
    runId: run.analysis_run_id,
    stale: data.source_draft_version !== currentDraftVersion,
    predictionUsed: run.predictionId !== null,
    maximum: data.level_one?.maximum_displacement || null,
    members,
    overlay,
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
    state,
  });
}

export function renderLevelOne(root, view) {
  root.replaceChildren();
  const title = document.createElement("h2"); title.textContent = "分析结果"; root.append(title);
  const status = document.createElement("p"); status.textContent = view.stale ? "当前结果对应较早的模型版本。" : "分析已完成，对应当前模型版本。"; root.append(status);
  const prediction = document.createElement("p"); prediction.textContent = view.predictionUsed ? "Prediction 已参与本次分析流程。" : "本次分析未绑定 Prediction。"; root.append(prediction);
  const maximum = document.createElement("p"); maximum.textContent = view.maximum ? `最大位移出现在 ${view.maximum.candidate_analysis_node_ids.join("、")}，大小为 ${view.maximum.maximum_displacement_mm} mm。` : "最大位移结论暂不可用。"; root.append(maximum);
  const legend = document.createElement("p"); legend.textContent = "图例：实线=受拉；虚线=受压；点划线=零杆。"; root.append(legend);
  for (const member of view.members) { const item = document.createElement("p"); item.textContent = `构件 ${member.physicalMemberClientKey}：${STATE_LABELS[member.state]}`; root.append(item); }
}
