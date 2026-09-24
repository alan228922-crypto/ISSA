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
    const analyzeContext = root.querySelector("[data-ux-analyze-context]");
    if (analyzeContext && stage === "analyze") analyzeContext.textContent = `将分析已保存的草稿 v${canvasController.getState().draftVersion}。${canvasController.getState().dirty ? "当前有未保存修改，请先保存模型。" : ""}`;
    const panel = root.querySelector("[data-ux-panel-title]");
    const guidance = root.querySelector("[data-ux-panel-guidance]");
    if (stage !== "build") {
      const messages = { check: ["模型检查", "检查已保存模型，再根据问题回到建模。"], prediction: ["先做判断", "预测可选；也可以跳过，直接分析。"], analyze: ["开始分析", "先确认保存的模型版本，再查看结果。"], understanding: ["理解结果", "先看结论，再选择预测对比、为什么或技术数据。"], summary: ["总结", "选择一次分析，整理计算依据和自己的设计说明。"] };
      if (panel) panel.textContent = messages[stage][0];
      if (guidance) guidance.textContent = messages[stage][1];
    } else {
      if (panel) panel.textContent = "当前任务";
      if (guidance) guidance.textContent = canvasController.getState().draft.nodes.length ? "选择工具后，点击画布或已有对象继续。" : "在画布点一下，放置第一个节点。";
    }
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
