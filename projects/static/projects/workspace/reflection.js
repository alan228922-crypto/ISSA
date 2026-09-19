import { postJson, requestJson, urlFromTemplate } from "./api.js";
import { normalizeApiError } from "./errors.js";

const FIELDS = Object.freeze([
  ["original_reasoning", "我原本是怎么判断这个结构的？"],
  ["unexpected_results", "哪些分析结果和我的预想不同？"],
  ["next_iteration_intent", "下一版我想修改什么，或重新观察什么？"],
]);

function failed(body) {
  const error = normalizeApiError(body);
  const exception = new Error(error.message);
  Object.assign(exception, error);
  return exception;
}

function reflectionUrl(template, runId) {
  return urlFromTemplate(template, { run_id: runId });
}

export function createReflectionWorkspace({ urls, request = postJson, get = requestJson, workflow = null, onChange = () => {} }) {
  let runId = null;
  let current = null;
  const state = () => current;
  const load = async (id) => {
    runId = id;
    const result = workflow ? await workflow.loadReflection(id) : await get(reflectionUrl(urls.reflectionTemplate, id));
    if (!workflow && !result.response.ok) {
      const error = normalizeApiError(result.body);
      if (result.response.status === 404 && error.code === "REFLECTION_NOT_FOUND") {
        current = null;
        onChange(current);
        return current;
      }
      throw failed(result.body);
    }
    current = workflow ? result : result.body;
    onChange(current);
    return current;
  };
  const save = async (fields) => {
    if (!Number.isInteger(runId)) throw new Error("Reflection run is not selected.");
    const result = workflow ? await workflow.saveReflection(runId, fields) : await request(reflectionUrl(urls.reflectionTemplate, runId), fields);
    if (!workflow && (!result.response.ok || !result.body?.ok)) throw failed(result.body);
    current = workflow ? result : result.body;
    onChange(current);
    return current;
  };
  const complete = async () => {
    if (!Number.isInteger(runId)) throw new Error("Reflection run is not selected.");
    const result = workflow ? await workflow.completeReflection(runId) : await request(reflectionUrl(urls.reflectionCompleteTemplate, runId), {});
    if (!workflow && (!result.response.ok || !result.body?.ok)) throw failed(result.body);
    current = workflow ? result : result.body;
    onChange(current);
    return current;
  };
  return Object.freeze({ loadReflection: load, saveReflection: save, completeReflection: complete, state });
}

export function renderReflection(root, reflection, { readOnly = false, onStart = () => {}, onSave = () => {}, onComplete = () => {}, onSkip = () => {} } = {}) {
  root.replaceChildren();
  const title = document.createElement("h2"); title.textContent = "反思"; root.append(title);
  if (!reflection) {
    const empty = document.createElement("p"); empty.textContent = "分析完成后可以记录反思，也可以稍后再说。"; root.append(empty);
    if (!readOnly) {
      const start = document.createElement("button"); start.type = "button"; start.textContent = "开始反思"; start.addEventListener("click", onStart); root.append(start);
      const skip = document.createElement("button"); skip.type = "button"; skip.textContent = "稍后再说"; skip.addEventListener("click", onSkip); root.append(skip);
    }
    return;
  }
  const completed = reflection.status === "COMPLETED";
  if (completed) {
    const note = document.createElement("p"); note.textContent = "这份 Reflection 已完成，不能修改。"; root.append(note);
  }
  const form = document.createElement("form");
  for (const [name, label] of FIELDS) {
    const field = document.createElement("label"); field.textContent = label;
    const textarea = document.createElement("textarea"); textarea.name = name; textarea.value = reflection[name] || ""; textarea.disabled = readOnly || completed; field.append(textarea); form.append(field);
  }
  if (!readOnly && !completed) {
    const save = document.createElement("button"); save.type = "button"; save.textContent = "保存草稿"; save.addEventListener("click", () => onSave(Object.fromEntries(FIELDS.map(([name]) => [name, form.elements[name].value])))); form.append(save);
    const complete = document.createElement("button"); complete.type = "button"; complete.textContent = "完成反思"; complete.addEventListener("click", onComplete); form.append(complete);
  }
  root.append(form);
  if (!completed) { const skip = document.createElement("button"); skip.type = "button"; skip.textContent = "稍后再说"; skip.addEventListener("click", onSkip); root.append(skip); }
}

export { FIELDS };
