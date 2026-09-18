import { postJson } from "./api.js";
import { normalizeApiError } from "./errors.js";

function failed(body) {
  const error = normalizeApiError(body);
  const exception = new Error(error.message);
  Object.assign(exception, error);
  return exception;
}

export function createWorkspaceWorkflow({ urls, request = postJson }) {
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
  });
}
