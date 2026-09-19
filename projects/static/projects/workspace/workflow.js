import { postJson, requestJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

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
  });
}
