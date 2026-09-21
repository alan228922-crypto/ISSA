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

async function optionalReflection(get, url) {
  const result = await get(url);
  if (result.response.status === 404 && result.body?.error?.code === "REFLECTION_NOT_FOUND") return null;
  if (!result.response.ok || !result.body?.ok) throw failure(result.body);
  return result.body;
}

export function createRunContext({ urls, select, editable = true, get = requestJson, onSelect = () => {} }) {
  let current = Object.freeze({ runs: Object.freeze([]), currentRunId: null, selectionToken: 0, payload: null });
  const state = () => current;
  const replaceOptions = (runs) => {
    select.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "请选择分析记录";
    select.append(placeholder);
    for (const run of runs) {
      const option = document.createElement("option");
      option.value = String(run.analysis_run_id);
      option.textContent = `分析 #${run.analysis_run_id} · ${run.status} · 草稿 v${run.source_draft_version}${run.is_stale ? " · 历史" : ""}`;
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
    if (metadata.status !== "SUCCESS") {
      const payload = Object.freeze({ metadata, status: metadata.status });
      if (current.selectionToken !== token) return null;
      current = Object.freeze({ ...current, payload });
      await onSelect(payload, token);
      return payload;
    }
    // Keep the requests in one run-scoped transaction sequence. This avoids a
    // later selection interleaving authoring state with an earlier Run.
    const data = await required(get, urlFromTemplate(urls.resultTemplate, { run_id: id }));
    const comparison = await required(get, urlFromTemplate(urls.comparisonTemplate, { run_id: id }));
    const explanation = await required(get, urlFromTemplate(urls.explanationTemplate, { run_id: id }));
    const report = await required(get, urlFromTemplate(urls.reportTemplate, { run_id: id }));
    const reasoning = editable ? await required(get, urlFromTemplate(urls.reasoningTemplate, { run_id: id })) : null;
    const reflection = editable ? await optionalReflection(get, urlFromTemplate(urls.reflectionTemplate, { run_id: id })) : null;
    if (current.selectionToken !== token || current.currentRunId !== id) return null;
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
    if (Number.isInteger(selectRunId) && runs.some((run) => run.analysis_run_id === selectRunId)) return selectRun(selectRunId);
    select.value = "";
    return runs;
  };
  return Object.freeze({ refreshRuns, selectRun, state });
}
