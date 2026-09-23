import { requestJson, postJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";
import { createStudentLabelResolver } from "./labels.js";

export const MEMBER_PREDICTION_CHOICES = Object.freeze(["TENSION", "COMPRESSION", "ZERO_FORCE", "UNSURE"]);

const MEMBER_LABELS = Object.freeze({ TENSION: "受拉", COMPRESSION: "受压", ZERO_FORCE: "近似零力", UNSURE: "不确定" });

function failure(body) {
  const error = normalizeApiError(body);
  const exception = new Error(error.message);
  Object.assign(exception, error);
  return exception;
}

function activeMembers(draft) {
  return (draft?.physical_members || []).filter((member) => member.is_active !== false).map((member) => member.client_key).sort();
}

function responsePrediction(body) {
  return body?.prediction || (body?.prediction_id ? body : null);
}

function endpointFromSelection(selection) {
  if (selection?.kind === "CONNECTION" && typeof selection.clientKey === "string") return { kind: "CONNECTION", connection_client_key: selection.clientKey };
  return null;
}

function pathEntityFromSelection(selection) {
  if (selection?.kind === "CONNECTION" && typeof selection.clientKey === "string") return { kind: "CONNECTION", connection_client_key: selection.clientKey };
  if (selection?.kind === "PHYSICAL_MEMBER" && typeof selection.clientKey === "string") return { kind: "PHYSICAL_MEMBER", physical_member_client_key: selection.clientKey };
  return null;
}

export function createPredictionWorkspace({ urls, draft: initialDraft, get = requestJson, post = postJson, onChange = () => {} }) {
  let draft = initialDraft;
  const memberKeys = () => activeMembers(draft);
  const emptyCurrent = () => ({ state: "NONE", loading: true, prediction: null, skipped: false, readonly: false, judgments: Object.fromEntries(memberKeys().map((key) => [key, "UNSURE"])), maximum: null, path: [] });
  let current = emptyCurrent();
  const state = () => Object.freeze({ ...current, judgments: { ...current.judgments }, maximum: current.maximum && { ...current.maximum }, path: current.path.map((entry) => ({ ...entry })) });
  const notify = () => onChange(state());
  const editable = () => current.state === "DRAFT" && !current.readonly;
  const restore = (mode, prediction) => {
    const payload = prediction?.payload || {};
    const judgments = Object.fromEntries(memberKeys().map((key) => [key, "UNSURE"]));
    for (const item of payload.member_judgments || []) if (memberKeys().includes(item.physical_member_client_key) && MEMBER_PREDICTION_CHOICES.includes(item.predicted_state)) judgments[item.physical_member_client_key] = item.predicted_state;
    current = { state: mode, loading: false, prediction: prediction || null, skipped: false, readonly: mode === "COMPLETED", judgments, maximum: payload.max_displacement_location || null, path: (payload.representative_load_path || []).map((entry) => ({ ...entry })) };
    notify();
  };
  const predictionPayload = () => ({ schema_version: "prediction-v1", member_judgments: memberKeys().map((key) => ({ physical_member_client_key: key, predicted_state: current.judgments[key] })), max_displacement_location: current.maximum, representative_load_path: current.path.map((entry) => ({ ...entry })) });

  return Object.freeze({
    async loadPrediction() {
      const result = await get(urls.current);
      if (!result.response.ok) {
        const error = failure(result.body);
        if (error.code === "PREDICTION_AMBIGUOUS") { current = { ...current, state: "AMBIGUOUS", loading: false, prediction: null, readonly: true }; notify(); return state(); }
        throw error;
      }
      restore(result.body?.state || "NONE", responsePrediction(result.body));
      return state();
    },
    async startPrediction() {
      if (current.loading || current.state === "AMBIGUOUS" || current.state === "COMPLETED") return state();
      const result = await post(urls.create, { expected_draft_version: draft.version });
      if (!result.response.ok || !result.body?.ok) throw failure(result.body);
      restore(result.body?.status === "COMPLETED" ? "COMPLETED" : "DRAFT", responsePrediction(result.body));
      return state();
    },
    setMemberJudgment(clientKey, predictedState) {
      if (!editable() || !memberKeys().includes(clientKey) || !MEMBER_PREDICTION_CHOICES.includes(predictedState)) return state();
      current = { ...current, skipped: false, judgments: { ...current.judgments, [clientKey]: predictedState } }; notify(); return state();
    },
    selectMaximumDisplacement(selection) {
      const point = endpointFromSelection(selection);
      if (!editable() || !point) return state();
      current = { ...current, skipped: false, maximum: point }; notify(); return state();
    },
    appendRepresentativePath(selection) {
      const entity = pathEntityFromSelection(selection);
      if (!editable() || !entity) return state();
      current = { ...current, skipped: false, path: [...current.path, entity] }; notify(); return state();
    },
    clearRepresentativePath() { if (editable()) { current = { ...current, skipped: false, path: [] }; notify(); } return state(); },
    predictionPayload,
    async completePrediction(payload = predictionPayload()) {
      if (current.state !== "DRAFT" || !current.prediction?.prediction_id) throw new Error("PREDICTION_NOT_DRAFT");
      const url = urlFromTemplate(urls.completeTemplate, { prediction_id: current.prediction.prediction_id });
      const result = await post(url, { expected_draft_version: draft.version, payload });
      if (!result.response.ok || !result.body?.ok) throw failure(result.body);
      restore("COMPLETED", responsePrediction(result.body) || { ...current.prediction, ...result.body, payload });
      return state();
    },
    skipPrediction() { if (current.state !== "COMPLETED" && current.state !== "AMBIGUOUS") { current = { ...current, skipped: true }; notify(); } return state(); },
    async refreshDraft(nextDraft) { draft = nextDraft; current = emptyCurrent(); notify(); return this.loadPrediction(); },
    predictionForAnalyze() { return current.state === "COMPLETED" && Number.isInteger(current.prediction?.prediction_id) ? current.prediction.prediction_id : null; },
    memberChoices: () => MEMBER_PREDICTION_CHOICES,
    memberKeys,
    state,
  });
}

function choiceButton(documentRef, member, choice, workspace) {
  const button = documentRef.createElement("button");
  button.type = "button";
  button.textContent = MEMBER_LABELS[choice];
  button.dataset.predictionChoice = choice;
  button.addEventListener("click", () => workspace.setMemberJudgment(member, choice));
  return button;
}

export function bindPredictionWorkspace({ root, urls, draft, canvasController, showError, get, post, readOnly = false, onStateChange = () => {} }) {
  const documentRef = root.ownerDocument;
  const status = root.querySelector("[data-prediction-status]");
  const members = root.querySelector("[data-prediction-members]");
  const maximum = root.querySelector("[data-prediction-maximum]");
  const path = root.querySelector("[data-prediction-path]");
  const start = root.querySelector("[data-prediction-start]");
  const complete = root.querySelector("[data-prediction-complete]");
  const skip = root.querySelector("[data-prediction-skip]");
  const selection = () => canvasController.getState().selectedObject;
  let workspace;
  const render = (view) => {
    const labels = createStudentLabelResolver(canvasController.getState().draft);
    onStateChange(view);
    status.textContent = view.loading ? "预测状态：加载中。" : view.state === "AMBIGUOUS" ? "当前预测记录存在数据歧义，暂时无法继续使用预测。请联系管理员处理。" : view.state === "COMPLETED" ? "预测状态：已完成，只读查看。" : view.state === "DRAFT" ? `预测状态：草稿${view.skipped ? "（已跳过，草稿已保留）" : "，可继续完成。"}` : view.skipped ? "预测状态：已跳过，可直接分析。" : "预测状态：尚未开始。";
    members.replaceChildren(...workspace.memberKeys().map((member) => { const row = documentRef.createElement("p"); row.textContent = `${labels.label("PHYSICAL_MEMBER", member)}：`; row.append(...MEMBER_PREDICTION_CHOICES.map((choice) => { const button = choiceButton(documentRef, member, choice, workspace); button.disabled = readOnly || view.loading || view.readonly || view.state !== "DRAFT"; button.setAttribute("aria-pressed", String(view.judgments[member] === choice)); return button; })); return row; }));
    maximum.textContent = view.maximum ? `最大位移预测位置：${view.maximum.connection_client_key ? labels.label("CONNECTION", view.maximum.connection_client_key) : `${labels.label("PHYSICAL_MEMBER", view.maximum.physical_member_client_key)} 的 ${view.maximum.endpoint} 端`}` : "最大位移预测位置：请在画布选择连接后设置。";
    path.textContent = view.path.length ? `代表性传力路径：${view.path.map((entry) => entry.connection_client_key ? labels.label("CONNECTION", entry.connection_client_key) : labels.label("PHYSICAL_MEMBER", entry.physical_member_client_key)).join(" → ")}` : "请选择你认为比较关键的一条传力路径。";
    start.hidden = view.state !== "NONE"; start.disabled = readOnly || view.loading; complete.disabled = readOnly || view.loading || view.state !== "DRAFT"; skip.disabled = readOnly || view.loading || view.state === "COMPLETED" || view.state === "AMBIGUOUS";
    root.querySelector("[data-prediction-maximum-select]").disabled = readOnly || view.loading || view.readonly || view.state !== "DRAFT";
    root.querySelector("[data-prediction-path-add]").disabled = readOnly || view.loading || view.readonly || view.state !== "DRAFT";
    root.querySelector("[data-prediction-path-clear]").disabled = readOnly || view.loading || view.readonly || view.state !== "DRAFT";
  };
  workspace = createPredictionWorkspace({ urls, draft, get, post, onChange: render });
  root.querySelector("[data-prediction-maximum-select]").addEventListener("click", () => workspace.selectMaximumDisplacement(selection()));
  root.querySelector("[data-prediction-path-add]").addEventListener("click", () => workspace.appendRepresentativePath(selection()));
  root.querySelector("[data-prediction-path-clear]").addEventListener("click", () => workspace.clearRepresentativePath());
  start.addEventListener("click", async () => { try { await workspace.startPrediction(); } catch (error) { showError(error); } });
  complete.addEventListener("click", async () => { try { await workspace.completePrediction(); } catch (error) { showError(error); } });
  skip.addEventListener("click", () => workspace.skipPrediction());
  const ready = workspace.loadPrediction().catch((error) => { showError(error); return workspace.state(); });
  render(workspace.state());
  return Object.freeze({ ...workspace, ready });
}
