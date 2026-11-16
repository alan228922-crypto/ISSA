import {createUiIcon} from "../../ui/icons.js";
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
  let current = null;
  let binding = { runId: null, epoch: null, queue: Promise.resolve() };
  const state = () => current;
  const useReflection = (id, reflection, epoch = null) => {
    binding = { runId: Number.isInteger(id) ? id : null, epoch, queue: Promise.resolve() };
    current = reflection;
    onChange(current);
    return current;
  };
  const perform = (operation, fields) => {
    const owner = binding;
    if (!Number.isInteger(owner.runId)) return Promise.reject(new Error("Reflection run is not selected."));
    const execute = async () => {
      if (binding !== owner) return null;
      try {
        let body;
        if (workflow) {
          body = await (operation === "load" ? workflow.loadReflection(owner.runId)
            : operation === "save" ? workflow.saveReflection(owner.runId, fields)
              : workflow.completeReflection(owner.runId));
        } else {
          const url = reflectionUrl(operation === "complete" ? urls.reflectionCompleteTemplate : urls.reflectionTemplate, owner.runId);
          const result = await (operation === "load" ? get(url) : request(url, operation === "save" ? fields : {}));
          if (operation === "load" && result.response.status === 404 && result.body?.error?.code === "REFLECTION_NOT_FOUND") body = null;
          else {
            if (!result.response.ok || !result.body?.ok) throw failed(result.body);
            body = result.body;
          }
        }
        if (binding !== owner) return null;
        if ((body === null && operation !== "load") || (body && (body.analysis_run_id !== owner.runId || !["DRAFT", "COMPLETED"].includes(body.status)))) {
          throw new Error("Reflection response does not belong to the selected analysis.");
        }
        current = body;
        onChange(current);
        return current;
      } catch (error) {
        if (binding !== owner) return null;
        throw error;
      }
    };
    const pending = owner.queue.then(execute);
    owner.queue = pending.catch(() => null);
    return pending;
  };
  const load = id => { useReflection(id, null); return perform("load"); };
  return Object.freeze({ loadReflection: load, saveReflection: fields => perform("save", fields),
    completeReflection: () => perform("complete"), useReflection, state });
}

export function renderReflection(root, reflection, { readOnly = false, onStart = () => {}, onSave = () => {}, onComplete = () => {}, onSkip = () => {} } = {}) {
  root.replaceChildren();
  const title = document.createElement("h2"); title.textContent = "反思";title.prepend(createUiIcon("reflect")); root.append(title);
  if(readOnly){const note=document.createElement("p");note.className="learning-notice";note.textContent="当前为只读查看，不能修改反思。";root.append(note);}
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
    const note = document.createElement("p"); note.className="learning-notice";note.textContent = "这份反思已完成，不能修改。"; root.append(note);
  }
  const form = document.createElement("form");
  const submit = async (action) => {
    const controls = [...form.querySelectorAll("button,textarea")];
    controls.forEach(control => { control.disabled = true; });
    try { await action(); }
    finally { controls.forEach(control => { control.disabled = readOnly || completed; }); }
  };
  for (const [name, label] of FIELDS) {
    const field = document.createElement("label"); field.textContent = label;
    const textarea = document.createElement("textarea"); textarea.name = name; textarea.value = reflection[name] || ""; textarea.disabled = readOnly || completed; field.append(textarea); form.append(field);
  }
  if (!readOnly && !completed) {
    const save = document.createElement("button"); save.type = "button"; save.textContent = "保存草稿"; save.addEventListener("click", () => submit(() => onSave(Object.fromEntries(FIELDS.map(([name]) => [name, form.elements[name].value]))))); save.prepend(createUiIcon("save"));form.append(save);
    const complete = document.createElement("button"); complete.type = "button"; complete.textContent = "完成反思"; complete.addEventListener("click", () => submit(onComplete)); complete.prepend(createUiIcon("check"));form.append(complete);
  }
  root.append(form);
  if (!completed) { const skip = document.createElement("button"); skip.type = "button"; skip.textContent = "稍后再说"; skip.addEventListener("click", onSkip); root.append(skip); }
}

export { FIELDS };
