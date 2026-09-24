import { postJson, requestJson, urlFromTemplate } from "./api.js";

const FIELDS = [["modeling_rationale", "建模说明", "为什么采用这样的结构形式和连接方式？"], ["material_section_rationale", "材料与截面说明", "为什么选择这些材料和截面？"], ["support_load_rationale", "支座与荷载说明", "为什么这样简化支座和荷载？"], ["result_interpretation", "结果理解", "你如何理解这次分析结果？"], ["design_change_rationale", "设计修改", "根据结果，你做了哪些修改？为什么？"], ["scheme_comparison", "方案比较", "不同方案之间有哪些差异和权衡？"], ["final_conclusion", "最终结论", "请用自己的话总结最终设计。"]];
export function bindReportReasoning({ root, template, get = requestJson, post = postJson, showError = () => {} }) {
  let activeRunId = null;
  let loadGeneration = 0;
  const url = (runId) => urlFromTemplate(template, { run_id: runId });
  const renderStatus = (message) => {
    root.replaceChildren();
    if (!message) return;
    const status = document.createElement("p");
    status.setAttribute("aria-live", "polite");
    status.textContent = message;
    root.append(status);
  };
  const renderEditor = (runId, reasoning = {}) => {
    root.replaceChildren();
    const title = document.createElement("h3");
    title.textContent = "我的设计说明";
    root.append(title);
    const notice = document.createElement("p"); notice.textContent = "由你自己填写，平台不会替你生成设计理由。"; root.append(notice);
    const overview = document.createElement("p"); overview.dataset.reasoningOverview = ""; root.append(overview);
    const form = document.createElement("form");
    const refreshOverview = () => { overview.textContent = `已填写 ${FIELDS.filter(([name]) => form.elements[name]?.value.trim()).length} / ${FIELDS.length} 项；可随时保存草稿。`; };
    for (const [index, [name, label, prompt]] of FIELDS.entries()) {
      if (index === 0 || index === 3 || index === 6) form.append(Object.assign(document.createElement("h4"), { textContent: index === 0 ? "结构与材料" : index === 3 ? "结果与修改" : "最终结论" }));
      const field = document.createElement("label"); field.textContent = `${label}：${prompt}`;
      const area = document.createElement("textarea"); area.name = name; area.value = reasoning[name] || "";
      area.addEventListener("input", refreshOverview);
      field.append(area); form.append(field);
    }
    const save = document.createElement("button"); save.type = "submit"; save.textContent = "保存设计说明";
    const status = document.createElement("p"); status.setAttribute("aria-live", "polite"); form.append(save, status);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (activeRunId !== runId) return;
      save.disabled = true; status.textContent = "正在保存…";
      try {
        const fields = Object.fromEntries(new FormData(form));
        const result = await post(url(runId), fields);
        if (!result.response.ok || !result.body?.ok || result.body.analysis_run_id !== runId) throw Object.assign(new Error(result.body?.error?.message || "保存失败"), result.body?.error);
        status.textContent = "设计说明已保存。";
      } catch (error) { status.textContent = "保存失败。"; showError(error); }
      finally { save.disabled = false; }
    });
    root.append(form);
    refreshOverview();
  };
  return Object.freeze({
    render(id, payload) {
      activeRunId = Number.isInteger(id) ? id : null;
      loadGeneration += 1;
      if (!activeRunId || !payload?.ok || payload.analysis_run_id !== activeRunId) { renderStatus(""); return; }
      renderEditor(activeRunId, payload.reasoning);
    },
    async load(id) {
      activeRunId = Number.isInteger(id) ? id : null;
      const requestedRunId = activeRunId;
      const generation = ++loadGeneration;
      if (!requestedRunId) { renderStatus(""); return; }
      renderStatus("正在加载这次分析的设计说明…");
      try {
        const result = await get(url(requestedRunId));
        if (generation !== loadGeneration || requestedRunId !== activeRunId) return;
        if (!result.response.ok || !result.body?.ok || result.body.analysis_run_id !== requestedRunId) throw Object.assign(new Error(result.body?.error?.message || "加载失败"), result.body?.error);
        renderEditor(requestedRunId, result.body.reasoning);
        return result.body;
      } catch (error) {
        if (generation !== loadGeneration || requestedRunId !== activeRunId) return;
        renderStatus("设计说明加载失败，请重新选择分析记录后重试。");
        showError(error);
        return null;
      }
    },
  });
}
