const STAGES = Object.freeze({
  build: ["建模", "放置第一个节点"],
  check: ["检查", "检查已保存的模型"],
  prediction: ["预测（可选）", "先记录你的判断，也可以直接分析"],
  analyze: ["分析", "分析这份已保存的模型"],
  understanding: ["理解", "先看结论，再查看证据"],
  summary: ["总结", "整理这次分析的依据和判断"],
});

function buildTask(draft) {
  if (!draft.nodes.length) return "放置第一个节点";
  if (!draft.physical_members.length) return "添加第二个节点，再用构件连接";
  if (!draft.connections.length) return "标明构件端点的连接";
  if (!draft.supports.length) return "为结构添加支座";
  if (!draft.node_loads.length) return "为结构添加荷载";
  return "保存模型，然后检查";
}

export function bindStudentShell({ root, canvasController }) {
  const current = root.querySelector("[data-ux-current-stage]");
  const next = root.querySelector("[data-ux-next-task]");
  const empty = root.querySelector("[data-ux-empty-state]");
  const saveIndicator = root.querySelector("[data-ux-save-indicator]");
  const saveStatus = root.querySelector("#workspace-save-status");
  function selectStage(stage) {
    if (!STAGES[stage]) return;
    root.dataset.uxStage = stage;
    current.textContent = `当前：${STAGES[stage][0]}`;
    next.textContent = `下一步：${stage === "build" ? buildTask(canvasController.getState().draft) : STAGES[stage][1]}`;
    for (const button of root.querySelectorAll("[data-ux-stage-target]")) {
      button.setAttribute("aria-current", button.dataset.uxStageTarget === stage ? "step" : "false");
    }
  }
  root.querySelectorAll("[data-ux-stage-target]").forEach(button => button.addEventListener("click", () => selectStage(button.dataset.uxStageTarget)));
  root.querySelector("[data-ux-start-modeling]")?.addEventListener("click", () => {
    selectStage("build");
    root.querySelector('[data-workspace-tool="NODE"]')?.click();
    if (empty) empty.hidden = true;
    root.querySelector("#workspace-canvas")?.focus();
  });
  root.querySelector('[data-workspace-tool="NODE"]')?.addEventListener("click", () => {
    if (empty) empty.hidden = true;
  });
  canvasController.subscribeStateChange(state => {
    if (empty && state.draft.nodes.length) empty.hidden = true;
    if (root.dataset.uxStage === "build") next.textContent = `下一步：${buildTask(state.draft)}`;
  });
  const syncSave = () => {
    const text = saveStatus.textContent;
    saveIndicator.textContent = text.includes("有") ? "有未保存修改" : "已保存";
  };
  new MutationObserver(syncSave).observe(saveStatus, { childList: true, characterData: true, subtree: true });
  syncSave();
  selectStage("build");
  return Object.freeze({ selectStage, setSaveState: (label) => { saveIndicator.textContent = label; } });
}
