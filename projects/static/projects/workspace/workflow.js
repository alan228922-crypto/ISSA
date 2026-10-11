import { postJson, requestJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

// Presentation only: server issue codes remain the sole validation authority.
const CHECK_RECOVERY = Object.freeze({
  NO_SUPPORT: { title: "缺少支座", explanation: "当前结构没有支承条件，尚不能进行分析。请在构件节点上添加适当支座。", actionLabel: "回建模添加支座", action: "SUPPORT" },
  INSUFFICIENT_RESTRAINT: { title: "支座约束不足", explanation: "现有支座不足以限制结构整体移动。请检查支座位置与限制的方向，再保存并重新检查。", actionLabel: "回建模检查支座", action: "SELECT" },
  SINGULAR_GLOBAL_STIFFNESS: { title: "结构可能不稳定", explanation: "结构可能整体移动或形成机构，暂时无法得到唯一解。请检查支座约束与构件连接；不能仅凭这项问题确定唯一原因。", actionLabel: "回建模检查支座与连接", action: "SELECT" },
  MISSING_MEMBER_START_NODE: { title: "构件缺少起点", explanation: "构件尚未指定起点，无法确定完整几何。请在对象属性中重新指定起点。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-start-node]" },
  MISSING_MEMBER_END_NODE: { title: "构件缺少终点", explanation: "构件尚未指定终点，无法确定完整几何。请在对象属性中重新指定终点。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-end-node]" },
  MISSING_MEMBER_MATERIAL: { title: "构件缺少材料", explanation: "构件缺少材料，无法确定刚度。请在对象属性中选择材料。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-material]" },
  MISSING_MEMBER_SECTION: { title: "构件缺少截面", explanation: "构件缺少截面，无法确定刚度。请在对象属性中选择截面。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-section]" },
  MISSING_CONNECTION_NODE: { title: "连接缺少位置", explanation: "连接尚未指定位置节点，请重新指定。缺漏补齐前不能分析。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-connection-node]" },
  MISSING_CONNECTION_PARTICIPANT: { title: "连接缺少参与构件", explanation: "连接的参与构件尚未完整，请重新指定。缺漏补齐前不能分析。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-participant]" },
  MISSING_SUPPORT_NODE: { title: "支座尚未指定作用节点", explanation: "支座没有明确作用位置，无法提供约束。请重新指定作用位置。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-support-target]" },
  MISSING_LOAD_NODE: { title: "荷载尚未指定作用节点", explanation: "荷载没有明确作用位置，不能进入分析。请在对象属性中重新指定作用节点。", actionLabel: "重新指定", action: "REBIND", field: "[data-property-load-target]" },
});

export function presentModelCheckIssue(issue, missingFields = []) {
  const presentation = Object.hasOwn(CHECK_RECOVERY, issue?.code) ? CHECK_RECOVERY[issue.code] : {
    title: "发现一个需要检查的地方",
    explanation: issue?.human_message || "模型需要进一步检查。",
    actionLabel: null, action: null,
  };
  if (issue?.physical_object?.kind !== "PHYSICAL_MEMBER" || missingFields.length < 2) return presentation;
  const bothEndpoints = missingFields.length === 2 && missingFields.includes("起点") && missingFields.includes("终点");
  const fields = missingFields.join(bothEndpoints ? "和" : "、");
  return { ...presentation, title: `构件缺少${fields}`, explanation: bothEndpoints
    ? "这根构件尚未指定起点和终点，因此无法确定完整位置。请重新指定两个端点。"
    : `这根构件尚未指定${fields}，缺漏补齐前不能分析。请在对象属性中逐项重新指定。` };
}

function failed(body) {
  const error = normalizeApiError(body);
  const exception = new Error(error.message);
  Object.assign(exception, error);
  return exception;
}

export function createWorkspaceWorkflow({ urls, request = postJson, get = requestJson }) {
  return Object.freeze({
    async saveDraft(draft) {
      const result = await request(urls.save, { ...draft, expected_draft_version: draft.version });
      if (!result.response.ok || !result.body?.ok) throw failed(result.body);
      return result.body;
    },
    async checkModel(version) {
      const result = await request(urls.check, { expected_draft_version: version });
      if (!result.response.ok) throw failed(result.body);
      return result.body;
    },
    async loadPrediction() { const result = await get(urls.prediction_current); if (!result.response.ok) throw failed(result.body); return result.body; },
    async createPrediction(version) { const result = await request(urls.prediction_create, { expected_draft_version: version }); if (!result.response.ok || !result.body?.ok) throw failed(result.body); return result.body; },
    async completePrediction(predictionId, version, payload) { const result = await request(urlFromTemplate(urls.prediction_complete_template, { prediction_id: predictionId }), { expected_draft_version: version, payload }); if (!result.response.ok || !result.body?.ok) throw failed(result.body); return result.body; },
    async analyze(version, predictionId) { const result = await request(urls.analyze, { expected_draft_version: version, prediction_id: predictionId }); if (!result.response.ok || !result.body?.ok) throw failed(result.body); return result.body; },
    async result(runId) { const result = await get(urlFromTemplate(urls.result_template, { run_id: runId })); if (!result.response.ok || !result.body?.ok) throw failed(result.body); return result.body; },
    async loadReflection(runId) {
      const result = await get(urlFromTemplate(urls.reflection_template, { run_id: runId }));
      if (result.response.status === 404 && result.body?.error?.code === "REFLECTION_NOT_FOUND") return null;
      if (!result.response.ok || !result.body?.ok) throw failed(result.body);
      return result.body;
    },
    async saveReflection(runId, fields) {
      const result = await request(urlFromTemplate(urls.reflection_template, { run_id: runId }), fields);
      if (!result.response.ok || !result.body?.ok) throw failed(result.body);
      return result.body;
    },
    async completeReflection(runId) {
      const result = await request(urlFromTemplate(urls.reflection_complete_template, { run_id: runId }), {});
      if (!result.response.ok || !result.body?.ok) throw failed(result.body);
      return result.body;
    },
  });
}
