import {createUiIcon} from "../../ui/icons.js";
import { formatVisualizationNumber } from "./analysis-visualization.js";
import { requestJson, postJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";
import { createStudentLabelResolver } from "./labels.js";
import { bindTabKeys } from "./student-shell.js";

const STATE_LABELS = Object.freeze({ TENSION: "受拉", COMPRESSION: "受压", ZERO: "近似零力", ZERO_FORCE: "近似零力", MIXED: "不同分析段的受力状态不同" });
const COMPARISON_LABELS = Object.freeze({ MATCH: "和预测一致", MISMATCH: "和预测不同", UNSURE: "之前选择“不确定”", NOT_COMPARABLE: "不能用单一类别直接对照" });

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

export function renderEngineeringDetails(root, details, stale = false, snapshot = {}, labels = createStudentLabelResolver(snapshot)) {
  const table = (title, headings, rows) => { const section = document.createElement("section"); const h = document.createElement("h3"); h.textContent = title; section.append(h); const t = document.createElement("table"); const head = document.createElement("tr"); headings.forEach((x) => { const th=document.createElement("th"); th.textContent=x; head.append(th); }); t.append(head); rows.forEach((row) => { const tr=document.createElement("tr"); row.forEach((x) => { const td=document.createElement("td"); td.textContent=x == null ? "—" : String(x); tr.append(td); }); t.append(tr); }); section.append(t); return section; };
  root.replaceChildren(); const note=document.createElement("p"); note.dataset.teachingContext = ""; note.textContent=stale ? "这份工程数据对应较早的模型版本，不能代表当前草稿。请重新分析当前模型，才能得到当前结果。" : "工程详情对应当前模型版本。"; root.append(note);
  root.append(table("节点位移",["节点","ux (mm)","uy (mm)"],details.displacements.map((x)=>[labels.analysisNode(x.analysis_node_id),x.ux_mm,x.uy_mm])));
  root.append(table("支座反力",["节点","Rx (N)","Ry (N)"],details.reactions.map((x)=>[labels.analysisNode(x.analysis_node_id),x.rx_N,x.ry_N])));
  root.append(table("构件工程数据",["构件","轴力 (N)","应力 (MPa)","质量 (g)"],details.members.map((x)=>[labels.analysisMember(x.physical_member_id,x.analysis_member_id),x.axial_force_N,x.axial_stress_MPa,x.mass_g])));
  const total=document.createElement("p"); total.textContent=details.total_mass_g === null ? "总质量：—" : `总质量：${details.total_mass_g} g`; root.append(total);
}

function failed(body) {
  const error = normalizeApiError(body);
  const exception = new Error(error.message);
  Object.assign(exception, error);
  return exception;
}

export function showLevelOne(view) {
  const members = (view.members || []).map(member => ({ physicalMemberClientKey: member.key,
    displayLabel: member.label, state: member.actualState }));
  const maximum = view.displacement;
  return Object.freeze({
    runId: view.runId,
    runNumber: view.runNumber || null,
    stale: view.historical,
    predictionUsed: view.comparisonAvailable === true,
    comparisonSummary: view.comparisonAvailable ? Object.entries(COMPARISON_LABELS).flatMap(([status, label]) => {
      const count = (view.members || []).filter(member => member.comparisonStatus === status).length;
      return count ? [`${label} ${count} 项`] : [];
    }).join("；") : "",
    maximum: maximum?.available ? {
      maximum_displacement_mm: maximum.maximumMm,
      candidate_analysis_node_ids: maximum.candidates.map(item => item.id),
      displayCandidateLabels: maximum.candidates.map(item => item.label),
    } : null,
    members,
    overlay: view.canLinkCanvas ? Object.fromEntries(members.map(member => [member.physicalMemberClientKey, member.state])) : {},
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
  const conclusion = document.createElement("section"); conclusion.dataset.resultConclusion = ""; conclusion.dataset.resultPanel = "conclusion"; root.append(conclusion);
  const title = document.createElement("h2"); title.textContent = view.runNumber ? `第 ${view.runNumber} 次分析 · 结论` : "这次分析 · 结论"; conclusion.append(title);
  const status = document.createElement("p"); status.dataset.resultContext = ""; status.textContent = view.stale ? "这份分析结果对应较早的模型版本，不能代表当前草稿。请重新分析当前模型，才能得到当前结果。" : "分析已完成，对应当前模型版本。"; conclusion.append(status);
  const overview=document.createElement("section");overview.dataset.resultOverview="";
  const overviewTitle=document.createElement("h4");overviewTitle.textContent="本次结论";overview.append(overviewTitle);
  const contextDetails=document.createElement("details");const contextSummary=document.createElement("summary");contextSummary.textContent="结论说明与构件";contextDetails.append(contextSummary);
  conclusion.append(overview);
  const prediction = document.createElement("p"); prediction.textContent = view.predictionUsed ? "预测已参与本次分析流程。" : "本次分析未使用预测。"; contextDetails.append(prediction);
  if (view.comparisonSummary) { const compared = document.createElement("p"); compared.textContent = `构件预测对照：${view.comparisonSummary}。可打开预测对比查看依据。`; contextDetails.append(compared); }
  const guidance = document.createElement("p"); guidance.textContent = "值得再看：从荷载位置出发，观察相连构件和支座。这里不推断唯一的传力路径。"; contextDetails.append(guidance);
  const maximum = document.createElement("p");
  if (view.maximum) {
    const raw = Number(view.maximum.maximum_displacement_mm);
    const rounded = raw !== 0 && Math.abs(raw) < .001 ? formatVisualizationNumber(raw) : raw.toLocaleString("zh-CN", { maximumFractionDigits: 3 });
    maximum.textContent = `最大位移出现在 ${(view.maximum.displayCandidateLabels || ['节点']).join("、")}，约为 `;
    const value = document.createElement("strong"); value.dataset.studentRoundedValue = ""; value.textContent = `${rounded} mm`; maximum.append(value, "。");
  } else maximum.textContent = "最大位移结论暂不可用。";
  overview.append(maximum);
  const counts = { TENSION: 0, COMPRESSION: 0, ZERO: 0, MIXED: 0 };
  for (const member of view.members) counts[member.state === "ZERO_FORCE" ? "ZERO" : member.state] = (counts[member.state === "ZERO_FORCE" ? "ZERO" : member.state] || 0) + 1;
  const summary = document.createElement("p"); summary.textContent = `受力状态概览：受拉 ${counts.TENSION}；受压 ${counts.COMPRESSION}；近似零力 ${counts.ZERO}；混合状态 ${counts.MIXED}。`; overview.append(summary);
  const legend = document.createElement("p"); legend.textContent = "图例：红色实线=受拉；蓝色虚线=受压；灰色点划线=近似零力；紫色分段=混合状态。"; contextDetails.append(legend);
  for (const member of view.members) {
    const item = document.createElement("button"); item.type = "button";
    item.dataset.teachingMember = member.physicalMemberClientKey;
    item.textContent = `${member.displayLabel || "构件"}：${STATE_LABELS[member.state]}`;
    item.addEventListener("click", () => focusPhysicalMember(member.physicalMemberClientKey, focus));
    overview.append(item);
  }
  overview.append(contextDetails);
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
    // Retain legacy action hooks without sharing the conclusion panel marker.
    button.dataset[name === "conclusion" ? "resultConclusionTab" : `result${name[0].toUpperCase()}${name.slice(1)}`] = "";
    button.textContent = text;
    button.addEventListener("click", () => { select(name); handler(); });
    actions.append(button);
  }
  const comparison = document.createElement("section");
  comparison.dataset.resultComparison = "";
  comparison.dataset.resultPanel = "compare";
  comparison.setAttribute("aria-live", "polite");
  const explanation = document.createElement("section");
  explanation.dataset.resultExplanation = "";
  explanation.dataset.resultPanel = "explain";
  explanation.setAttribute("aria-live", "polite");
  root.prepend(actions);
  root.append(comparison, explanation);
  bindTabKeys(actions);
  select("conclusion");
}

function appendMemberEvidence(root, item) {
  if (item.actualState === "MIXED") {
    const explanation = document.createElement("p");
    explanation.textContent = "一根实际构件在分析模型中可能被分成多个分析段，这些分析段的受力状态并不完全相同。";
    root.append(explanation);
  }
  if (item.actualState === "ZERO_FORCE") {
    const caveat = document.createElement("p"); caveat.textContent = "近似零力是教学分类，不表示轴力数学上严格等于 0。"; root.append(caveat);
  }
  const details = document.createElement("details"); const summary = document.createElement("summary"); summary.textContent = "查看全部分析段证据"; details.append(summary);
  const list = document.createElement("ul");
  for (const segment of item.segments || []) {
    const evidence = document.createElement("li");
    const force = Number.isFinite(segment.axial_force_N) ? `，轴力 ${segment.axial_force_N} N` : "";
    evidence.textContent = `${segment.label}：${STATE_LABELS[segment.teaching_state] || "状态暂不可用"}${force}。`;
    list.append(evidence);
  }
  details.append(list); root.append(details);
}

function appendReflectionNavigation(root, onReflect) {
  const button = document.createElement("button"); button.type = "button"; button.dataset.evidenceReflect = "";
  button.textContent = "进入反思"; button.addEventListener("click", onReflect); root.append(button);
}

export function teachingContextText(view) {
  return `${view.runLabel} · 已分析模型草稿 v${view.sourceDraftVersion}${view.historical ? " · 历史证据，不代表当前草稿" : " · 所选分析的数值与来源"}`;
}

export function renderComparison(root, view, { onFocusMember = () => {}, onReflect = () => {} } = {}) {
  root.replaceChildren();
  const heading=document.createElement("h2");heading.textContent="我的预测与分析证据";heading.prepend(createUiIcon("check"));root.append(heading);
  if (view.available) { const context = document.createElement("p"); context.dataset.teachingContext = ""; context.textContent = teachingContextText(view); root.append(context); }
  if (!view.available || !view.comparisonAvailable) {
    const note = document.createElement("p");
    note.textContent = view.available ? "这次没有保存预测，因此暂时无法比较。仍可查看实际结果和说明。" : "这次分析的对照证据暂不可用，请重新选择分析记录。";
    root.append(note);
    return;
  }
  for (const item of view.members.filter(member => member.comparisonStatus)) {
    const section = document.createElement("section");
    section.dataset.comparisonEvidenceMember = item.key;section.dataset.comparisonStatus=item.comparisonStatus;section.className="learning-card";
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.comparisonMember = item.key;
    button.dataset.teachingMember = item.key;
    button.textContent = `${item.label}：${COMPARISON_LABELS[item.comparisonStatus]}`;
    button.addEventListener("click", () => onFocusMember(item.key));
    section.append(button);
    const states = document.createElement("div");states.className="learning-comparison-pair";
    for(const text of [`预测：${item.predictedState === "UNSURE" ? "不确定" : STATE_LABELS[item.predictedState]}`,`分析：${STATE_LABELS[item.actualState]}`]){const cell=document.createElement("p");cell.textContent=text;states.append(cell);}section.append(states);
    appendMemberEvidence(section, item);
    root.append(section);
  }
  if (view.hypothesis?.length) {
    const section = document.createElement("section"); section.dataset.studentHypothesis = "";
    const title = document.createElement("h3"); title.textContent = "学生传力假设";
    const prompt = document.createElement("p"); prompt.textContent = "这些结果是否支持你的判断？"; section.append(title, prompt);
    for (const member of view.hypothesis) { const name = document.createElement("p"); name.textContent = member.label; section.append(name); appendMemberEvidence(section, member); }
    root.append(section);
  }
  const displacement = document.createElement("section");
  const title = document.createElement("h3"); title.textContent = "最大位移位置对照"; displacement.append(title);
  if (!view.displacement?.available) {
    const note = document.createElement("p"); note.textContent = "这次分析的位移对照证据暂不可用，请重新选择分析记录后重试。"; displacement.append(note);
  } else {
    const facts = view.displacement;
    const predicted = document.createElement("p"); predicted.textContent = `预测位置：${facts.predictedLocationLabel}。`; displacement.append(predicted);
    const magnitude = document.createElement("p"); magnitude.textContent = `实际最大位移：${facts.maximumMm} mm。以下位置均为最大位移候选：`; displacement.append(magnitude);
    const list = document.createElement("ul");
    for (const candidate of facts.candidates) {
      const row = document.createElement("li"); row.dataset.maximumCandidate = ""; row.textContent = candidate.label; list.append(row);
    }
    displacement.append(list);
    const outcome = document.createElement("p"); outcome.textContent = facts.locationMatch ? "预测位置与最大位移候选位置一致。" : "预测位置与最大位移候选位置不同，可以对照这些位置再观察。"; displacement.append(outcome);
  }
  root.append(displacement);
  appendReflectionNavigation(root, onReflect);
}

export function renderExplanation(root, view, { onFocusMember = () => {}, onReflect = () => {} } = {}) {
  root.replaceChildren();
  const paragraph = (parent, text) => { const p = document.createElement("p"); p.textContent = text; parent.append(p); };
  if (!view.available) { paragraph(root, "这次分析的证据暂不可用，请重新选择分析记录后重试。"); return; }
  const heading=document.createElement("h2");heading.textContent="从结论理解工程证据";heading.prepend(createUiIcon("book"));root.append(heading);
  const visibleContext=document.createElement("p");visibleContext.dataset.learningVisibleContext="";visibleContext.dataset.historical=String(Boolean(view.historical));visibleContext.textContent=teachingContextText(view);root.append(visibleContext);
  const levels = [];
  for (const [index, title] of ["发生了什么？", "依据是什么？", "具体数值与来源"].entries()) {
    const level = document.createElement("section"); level.dataset.teachingLevel = String(index + 1);level.dataset.learningStep=String(index+1);
    const kicker=document.createElement("p");kicker.className="learning-kicker";kicker.textContent=["01 / 结论","02 / 原因","03 / 工程证据"][index];level.append(kicker);
    const heading = document.createElement("h3"); heading.textContent = title; level.append(heading); levels.push(level);
  }
  paragraph(levels[1], "以下受力状态来自所选分析段的轴力；具体数值可展开查看。");
  const context = document.createElement("p"); context.dataset.teachingContext = ""; context.textContent = teachingContextText(view); levels[2].append(context);
  for (const item of view.explanationBlocks) {
    for (let index = 0; index < levels.length; index += 1) {
      const section = document.createElement("section");section.className="learning-card";
      const heading = document.createElement(index === 0 && item.memberKey ? "button" : "h4");
      heading.textContent = item.label;
      if (heading.tagName === "BUTTON") {
        heading.type = "button"; heading.dataset.teachingMember = item.memberKey;
        heading.addEventListener("click", () => onFocusMember(item.memberKey));
      }
      section.append(heading);
      const text = document.createElement("p"); text.dataset.explanationBlock = "";
      text.textContent = item.messages[`level_${index + 1}`]; section.append(text);
      if (index > 0 && item.segments.length) {
        const list = document.createElement("ul");
        for (const segment of item.segments) {
          const row = document.createElement("li");
          row.textContent = `${segment.label}：${STATE_LABELS[segment.teaching_state] || "状态暂不可用"}${index === 2 && Number.isFinite(segment.axial_force_N) ? `，轴力 ${segment.axial_force_N} N` : ""}`;
          list.append(row);
        }
        section.append(list);
      }
      if (index > 0 && item.candidates.length) {
        const list = document.createElement("ul");
        for (const candidate of item.candidates) {
          const row = document.createElement("li"); row.textContent = candidate.label;
          if (index === 2) row.textContent += `：ux ${candidate.uxMm} mm，uy ${candidate.uyMm} mm，位移大小 ${candidate.magnitudeMm} mm`;
          list.append(row);
        }
        section.append(list);
      }
      levels[index].append(section);
    }
  }
  const professional = document.createElement("details");
  const summary = document.createElement("summary"); summary.textContent = "查看具体数值与来源";
  professional.append(summary, levels[2]); root.append(levels[0], levels[1], professional);
  appendReflectionNavigation(root, onReflect);
}


export function attachAnalysisVisualization(root, element, {runNumber=null,onTechnical=()=>{}}={}) {
  let conclusion=root.querySelector('[data-result-panel="conclusion"]');
  if(!conclusion){
    conclusion=document.createElement('section');conclusion.dataset.resultPanel='conclusion';conclusion.dataset.av01PendingConclusion='';
    const title=document.createElement('h2');title.textContent=runNumber?`第 ${runNumber} 次分析 · 结构视图`:'所选分析 · 结构视图';
    const notice=document.createElement('p');notice.textContent='图形与数值属于所选分析；教学说明按可用资料显示。';conclusion.append(title,notice);root.append(conclusion);
    if(!root.querySelector('[role="tablist"]')){
      const unavailable=selector=>{const panel=root.querySelector(selector);panel.replaceChildren();const p=document.createElement('p');p.textContent='这次分析的教学说明暂不可用；仍可在结论查看已保存的工程数值。';panel.append(p);};
      renderResultActions(root,{onCompare:()=>unavailable('[data-result-comparison]'),onExplain:()=>unavailable('[data-result-explanation]'),onTechnical});
    }
  }
  const overview=conclusion.querySelector(':scope > [data-result-overview]'),slot=element.querySelector('[data-av01-conclusion-slot]');
  if(overview&&slot)slot.replaceChildren(overview);
  if(element.parentElement!==conclusion)conclusion.insertBefore(element,conclusion.children[2]||null);
}
