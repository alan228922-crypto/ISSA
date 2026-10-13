import { studentObjectName } from "./incomplete-objects.js";

const TYPES = { GEOMETRY_NODE: "节点", PHYSICAL_MEMBER: "构件", SUPPORT: "支座", NODE_LOAD: "荷载" };
const countText = counts => Object.entries(TYPES).filter(([kind]) => counts[kind]).map(([kind, name]) => `${counts[kind]} 个${name}`).join(" · ") || "无";

export function confirmDeleteImpact({ workspace, originalDraft, preview }) {
  const dialog = workspace.querySelector("[data-delete-impact-dialog]");
  const previousFocus = document.activeElement;
  const restoreFocus = () => (previousFocus?.isConnected ? previousFocus : workspace.querySelector("#workspace-canvas"))?.focus({ preventScroll: true });
  const content = dialog.querySelector("[data-delete-impact-content]");
  content.replaceChildren();
  const text = (value, marker) => {
    const element = document.createElement("p"); element.textContent = value;
    if (marker) element.dataset[marker] = "";
    content.append(element);
  };
  text("这些物件会失去连接或作用位置。");
  text(countText(preview.summary.related), "deleteImpactRelatedSummary");
  text("以下为「一起删除相关物件」的完整影响范围。保留选项只删除已选对象。");
  text("保留后，部分物件可能不会显示在画布上，但仍会保存在模型中。");
  text(`已选对象：${countText(preview.summary.selected)}`);
  text(`一起删除合计：${countText(preview.summary.total)}`, "deleteImpactTotalSummary");
  const details = document.createElement("details");
  const summary = document.createElement("summary"); summary.textContent = "查看受影响物件"; details.append(summary);
  for (const [title, targets] of [["删除已选对象后受影响", preview.directAffected], ["一起删除相关构件后额外受影响", preview.newlyUnattached]]) {
    if (!targets.length) continue;
    const heading = document.createElement("h3"); heading.textContent = title; details.append(heading);
    const list = document.createElement("ul");
    for (const target of targets) {
      const item = document.createElement("li"); item.textContent = studentObjectName(originalDraft, target.kind, target.clientKey); list.append(item);
    }
    details.append(list);
  }
  content.append(details);
  return new Promise(resolve => {
    const listeners = new AbortController();
    let settled = false;
    const finish = choice => {
      if (settled) return;
      settled = true;
      listeners.abort(); dialog.close();
      resolve({ choice, restoreFocus });
    };
    for (const button of dialog.querySelectorAll("[data-delete-impact-choice]")) {
      button.addEventListener("click", () => finish(button.dataset.deleteImpactChoice), { signal: listeners.signal });
    }
    dialog.addEventListener("cancel", event => { event.preventDefault(); finish("cancel"); }, { signal: listeners.signal });
    // Existing Canvas handlers bubble on document. Isolate them here while native
    // Tab, Enter and Space activation still work inside the modal dialog.
    const isolate = event => {
      if (!dialog.open) return;
      // Release cleanup must reach the existing owners of held-key state. It is
      // not a selection command; suppress any Space-tap repeat it would emit below.
      if (event.type === "keyup" && (event.code === "Space" || event.key === "Shift")) return;
      event.stopImmediatePropagation();
      if (event.type === "keydown" && event.key === "Escape") { event.preventDefault(); finish("cancel"); }
      else if (["Delete", "Backspace"].includes(event.key)) event.preventDefault();
    };
    document.addEventListener("keydown", isolate, { capture: true, signal: listeners.signal });
    document.addEventListener("keyup", isolate, { capture: true, signal: listeners.signal });
    document.addEventListener("cad-space-tap", event => { if (dialog.open) event.stopImmediatePropagation(); }, { capture: true, signal: listeners.signal });
    dialog.showModal();
    dialog.querySelector('[data-delete-impact-choice="cancel"]').focus();
  });
}
