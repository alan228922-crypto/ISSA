import { requestJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

function failure(body) {
  const error = normalizeApiError(body);
  return Object.assign(new Error(error.message), error);
}

async function required(get, url) {
  const result = await get(url);
  if (!result.response.ok || !result.body?.ok) throw failure(result.body);
  return result.body;
}

async function optionalReflection(get, url, { deniedAsEmpty = false } = {}) {
  const result = await get(url);
  if (result.response.status === 404 && result.body?.error?.code === "REFLECTION_NOT_FOUND") return null;
  if (deniedAsEmpty && result.response.status === 403) return null;
  if (!result.response.ok || !result.body?.ok) throw failure(result.body);
  return result.body;
}

export function createRunContext({ urls, select, editable = true, get = requestJson, onSelect = () => {}, onRunsChange = () => {} }) {
  let current = Object.freeze({ runs: Object.freeze([]), currentRunId: null, selectionToken: 0, payload: null });
  const state = () => current;
  const replaceOptions = (runs) => {
    const chronological = [...runs].sort((left, right) => left.analysis_run_id - right.analysis_run_id);
    select.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "请选择分析记录";
    select.append(placeholder);
    for (const run of runs) {
      const option = document.createElement("option");
      option.value = String(run.analysis_run_id);
      option.textContent = `第 ${chronological.findIndex(item => item.analysis_run_id === run.analysis_run_id) + 1} 次分析 · ${run.status === "SUCCESS" ? "已完成" : "未完成"}${run.is_stale ? " · 较早模型" : ""}`;
      select.append(option);
    }
  };
  const selectRun = async (runId) => {
    const id = Number(runId);
    if (!Number.isInteger(id)) {
      const token = current.selectionToken + 1;
      current = Object.freeze({ ...current, currentRunId: null, selectionToken: token, payload: null });
      select.value = "";
      await onSelect(null, token);
      return null;
    }
    const metadata = current.runs.find((run) => run.analysis_run_id === id);
    if (!metadata) throw Object.assign(new Error("请选择列表中的分析记录。"), { code: "RUN_NOT_DISCOVERED" });
    const token = current.selectionToken + 1;
    current = Object.freeze({ ...current, currentRunId: id, selectionToken: token, payload: null });
    select.value = String(id);
    await onSelect(null, token);
    if (metadata.status !== "SUCCESS") {
      const payload = Object.freeze({ metadata, status: metadata.status });
      if (current.selectionToken !== token) return null;
      current = Object.freeze({ ...current, payload });
      await onSelect(payload, token);
      return payload;
    }
    const obsolete = () => current.selectionToken !== token || current.currentRunId !== id;
    let data; let comparison; let explanation; let report; let reasoning; let reflection;
    try {
      data = await required(get, urlFromTemplate(urls.resultTemplate, { run_id: id })); if (obsolete()) return null;
      comparison = await required(get, urlFromTemplate(urls.comparisonTemplate, { run_id: id })); if (obsolete()) return null;
      explanation = await required(get, urlFromTemplate(urls.explanationTemplate, { run_id: id })); if (obsolete()) return null;
      report = await required(get, urlFromTemplate(urls.reportTemplate, { run_id: id })); if (obsolete()) return null;
      reasoning = editable ? await required(get, urlFromTemplate(urls.reasoningTemplate, { run_id: id })) : null; if (obsolete()) return null;
      reflection = await optionalReflection(get, urlFromTemplate(urls.reflectionTemplate, { run_id: id }), { deniedAsEmpty: !editable });
    } catch (error) {
      if (obsolete()) return null;
      throw error;
    }
    if (obsolete()) return null;
    const payload = Object.freeze({ metadata, status: "SUCCESS", data, comparison: comparison.comparison, explanation: explanation.explanation, report, reasoning, reflection });
    current = Object.freeze({ ...current, payload });
    await onSelect(payload, token);
    return payload;
  };
  const refreshRuns = async ({ selectRunId = null } = {}) => {
    const result = await required(get, urls.runs);
    const runs = Object.freeze([...(result.runs || [])].map((run) => Object.freeze({ ...run })));
    current = Object.freeze({ ...current, runs });
    replaceOptions(runs);
    onRunsChange(runs);
    if (Number.isInteger(selectRunId) && runs.some((run) => run.analysis_run_id === selectRunId)) return selectRun(selectRunId);
    select.value = "";
    return runs;
  };
  return Object.freeze({ refreshRuns, selectRun, state });
}
