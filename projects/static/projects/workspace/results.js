import { requestJson, postJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

const STATE_LABELS = Object.freeze({ TENSION: "受拉", COMPRESSION: "受压", ZERO: "零杆", ZERO_FORCE: "零杆" });

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
