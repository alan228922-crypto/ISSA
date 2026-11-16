import { requestJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

function failure(body) {
  const error = normalizeApiError(body);
  return Object.assign(new Error(error.message), error);
}

async function required(get, url) {
  const result = await get(url);
  if (!result.response.ok || !result.body?.ok) throw Object.assign(failure(result.body),{status:result.response.status});
  return result.body;
}

async function optionalReflection(get, url, { deniedAsEmpty = false } = {}) {
  const result = await get(url);
  if (result.response.status === 404 && result.body?.error?.code === "REFLECTION_NOT_FOUND") return null;
  if (deniedAsEmpty && result.response.status === 403) return null;
  if (!result.response.ok || !result.body?.ok) throw Object.assign(failure(result.body),{status:result.response.status});
  return result.body;
}

export function createRunContext({ urls, select, editable = true, get = requestJson, onSelect = () => {}, onRunsChange = () => {}, projectId = null, onVisualization = () => {} }) {
  let current = Object.freeze({ runs: Object.freeze([]), currentRunId: null, selectionToken: 0, payload: null });
  let refreshGeneration = 0;
  let visualizationAnchor=null,visualizationRequest=0,visualizationAbort=null,deniedToken=null;
  const visualizationEnabled=typeof urls.visualizationTemplate==='string';
  const resetVisualization=()=>{visualizationAnchor=null;visualizationRequest++;visualizationAbort?.abort();visualizationAbort=null;deniedToken=null;};
  const isDenied=value=>[401,403].includes(value?.status)||(value?.status===404&&['PROJECT_NOT_FOUND','ANALYSIS_RUN_NOT_FOUND'].includes(value?.code));
  const emitVisualization=(kind,metadata,epoch,extra={})=>onVisualization(Object.freeze({kind,runId:metadata.analysis_run_id,epoch,metadata,...extra}));
  const selectionOwns=(metadata,token)=>current.currentRunId===metadata.analysis_run_id&&current.selectionToken===token;
  const denyVisualization=async(metadata,token)=>{
    if(!selectionOwns(metadata,token))return;
    deniedToken=token;visualizationAnchor=null;visualizationRequest++;visualizationAbort?.abort();visualizationAbort=null;
    current=Object.freeze({...current,payload:null});await onSelect(null,token);
    if(selectionOwns(metadata,token))emitVisualization('DENIED',metadata,token);
  };
  const dataAnchor=(metadata,data)=>{
    if(!Number.isInteger(projectId)||projectId<=0||data?.status!=='SUCCESS'
      ||data.analysis_run_id!==metadata.analysis_run_id||data.model_revision_id!==metadata.model_revision_id
      ||data.source_draft_version!==metadata.source_draft_version
      ||![metadata.analysis_run_id,metadata.model_revision_id,metadata.source_draft_version].every(Number.isInteger)
      ||!['model_hash','input_hash'].every(key=>typeof data[key]==='string'&&/^[a-f0-9]{64}$/i.test(data[key]))
      ||!['input_schema_version','result_schema_version'].every(key=>typeof data[key]==='string'&&data[key].length))return null;
    return Object.freeze({projectId,runId:metadata.analysis_run_id,revisionId:metadata.model_revision_id,sourceDraftVersion:metadata.source_draft_version,
      modelHash:data.model_hash,inputHash:data.input_hash,inputSchemaVersion:data.input_schema_version,resultSchemaVersion:data.result_schema_version});
  };
  const requestVisualization=async(metadata,token)=>{
    if(!visualizationEnabled||!visualizationAnchor||!selectionOwns(metadata,token)||deniedToken===token)return false;
    const expectedContext=visualizationAnchor,request=++visualizationRequest;
    visualizationAbort?.abort();visualizationAbort=new AbortController();
    const obsolete=()=>!selectionOwns(metadata,token)||request!==visualizationRequest||deniedToken===token;
    emitVisualization('LOADING',metadata,token);
    let result;
    try{result=await get(urlFromTemplate(urls.visualizationTemplate,{run_id:metadata.analysis_run_id}),{signal:visualizationAbort.signal});}
    catch(error){if(obsolete())return false;emitVisualization('ERROR',metadata,token);return false;}
    if(obsolete())return false;
    if(!result.response.ok||!result.body?.ok){
      const error=Object.assign(failure(result.body),{status:result.response.status});
      if(isDenied(error))await denyVisualization(metadata,token);else emitVisualization(result.response.status===422?'UNAVAILABLE':'ERROR',metadata,token);
      return false;
    }
    const projection=result.body.visualization;
    if(!['READY','PARTIAL'].includes(projection?.status)||projection.capabilities?.geometry?.status!=='READY'){emitVisualization('UNAVAILABLE',metadata,token);return false;}
    emitVisualization('READY',metadata,token,{expectedContext,projection});return true;
  };
  const retryVisualization=()=>{
    const metadata=current.runs.find(run=>run.analysis_run_id===current.currentRunId);
    return metadata?requestVisualization(metadata,current.selectionToken):Promise.resolve(false);
  };
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
    if (runId === null || runId === "" || !Number.isInteger(id)) {
      resetVisualization();
      const token = current.selectionToken + 1;
      current = Object.freeze({ ...current, currentRunId: null, selectionToken: token, payload: null });
      select.value = "";
      await onSelect(null, token);
      return null;
    }
    const metadata = current.runs.find((run) => run.analysis_run_id === id);
    if (!metadata) throw Object.assign(new Error("请选择列表中的分析记录。"), { code: "RUN_NOT_DISCOVERED" });
    resetVisualization();
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
    const obsolete = () => current.selectionToken !== token || current.currentRunId !== id || deniedToken===token;
    if(visualizationEnabled)emitVisualization('LOADING',metadata,token);
    let data; let comparison; let explanation; let report; let reasoning; let reflection;
    try {
      data = await required(get, urlFromTemplate(urls.resultTemplate, { run_id: id })); if (obsolete()) return null;
      if(visualizationEnabled){visualizationAnchor=dataAnchor(metadata,data);if(visualizationAnchor)void requestVisualization(metadata,token);else emitVisualization('UNAVAILABLE',metadata,token);}
      comparison = await required(get, urlFromTemplate(urls.comparisonTemplate, { run_id: id })); if (obsolete()) return null;
      explanation = await required(get, urlFromTemplate(urls.explanationTemplate, { run_id: id })); if (obsolete()) return null;
      report = await required(get, urlFromTemplate(urls.reportTemplate, { run_id: id })); if (obsolete()) return null;
      reasoning = editable ? await required(get, urlFromTemplate(urls.reasoningTemplate, { run_id: id })) : null; if (obsolete()) return null;
      reflection = await optionalReflection(get, urlFromTemplate(urls.reflectionTemplate, { run_id: id }), { deniedAsEmpty: !editable });
    } catch (error) {
      if (obsolete()) return null;
      if(visualizationEnabled&&isDenied(error))await denyVisualization(metadata,token);
      throw error;
    }
    if (obsolete()) return null;
    const payload = Object.freeze({ metadata, status: "SUCCESS", data, comparison: comparison.comparison, explanation: explanation.explanation, report, reasoning, reflection });
    current = Object.freeze({ ...current, payload });
    await onSelect(payload, token);
    return payload;
  };
  const refreshRuns = async ({ selectRunId = null } = {}) => {
    const generation = ++refreshGeneration;
    // Clear synchronously, before requesting a new list; don't keep obsolete panels visible.
    const clearing = selectRun(null);
    const token = current.selectionToken;
    const request = required(get, urls.runs);
    const obsolete = () => generation !== refreshGeneration || token !== current.selectionToken;
    let result;
    try {
      await clearing;
      result = await request;
    } catch (error) {
      if (obsolete()) return null;
      throw error;
    }
    if (obsolete()) return null;
    const runs = Object.freeze([...(result.runs || [])].map((run) => Object.freeze({ ...run })));
    current = Object.freeze({ ...current, runs });
    replaceOptions(runs);
    onRunsChange(runs);
    if (Number.isInteger(selectRunId) && runs.some((run) => run.analysis_run_id === selectRunId)) return selectRun(selectRunId);
    select.value = "";
    return runs;
  };
  return Object.freeze({ refreshRuns, selectRun, state, retryVisualization });
}
