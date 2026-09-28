import { EditorActionError } from "./editor.js";
import { applyWorkspaceEditorAction } from "./state.js";
import { createStudentLabelResolver } from "./labels.js";

const OBJECTS = Object.freeze({
  GEOMETRY_NODE: { collection: "nodes", label: "节点" },
  PHYSICAL_MEMBER: { collection: "physical_members", label: "构件" },
  CONNECTION: { collection: "connections", label: "连接" },
  SUPPORT: { collection: "supports", label: "支座" },
  NODE_LOAD: { collection: "node_loads", label: "荷载" },
});
const propertyEditing = new WeakSet();
let deleteFeedback = "";

function hasTargetLocation(draft, targetConnectionKey) {
  if (!targetConnectionKey) return false;
  return Boolean(draft.connections.find((item) => item.client_key === targetConnectionKey)?.geometry_node_client_key);
}

function selectedRecord(state) {
  const selected = state.selectedObject;
  const definition = OBJECTS[selected?.kind];
  if (!definition) return null;
  const record = state.draft[definition.collection]?.find((item) => item.client_key === selected.clientKey);
  return record ? { definition, record, selected } : null;
}

function updateState(canvasController, action, showError = null) {
  const current = canvasController.getState();
  try {
    const next = applyWorkspaceEditorAction(current, action);
    if (next !== current) {
      propertyEditing.add(canvasController);
      try { canvasController.replaceState(next); }
      finally { propertyEditing.delete(canvasController); }
    }
    document.getElementById("workspace-save-status").textContent = next.dirty ? "未保存修改：有" : "未保存修改：无";
  } catch (error) {
    if (!(error instanceof EditorActionError) || !showError) throw error;
    showError({ code: error.code, message: error.code === "EDITOR_NODE_MOVE_BREAKS_CONNECTION" ? "移动会使连接脱离构件，原节点未移动。" : "此位置会使构件长度为零，原节点未移动。" });
    canvasController.replaceState(current);
  }
}

function labeledInput(root, { text, value, type = "text", dataName, onChange }) {
  const label = document.createElement("label");
  label.textContent = text;
  const input = document.createElement("input");
  input.type = type;
  if (type === "number") input.step = "any";
  input.dataset[dataName] = "";
  input.value = String(value ?? "");
  input.addEventListener("change", () => onChange(input));
  label.append(input);
  root.append(label);
}

function appendLabelControl(root, selected, record, canvasController) {
  labeledInput(root, { text: "标签", value: record.label, dataName: "propertyLabel", onChange: (input) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { label: input.value } });
  } });
}

function appendNodeControls(root, selected, node, canvasController, showError) {
  for (const [field, text, dataName] of [["x_mm", "X（mm）", "propertyX"], ["y_mm", "Y（mm）", "propertyY"]]) {
    labeledInput(root, { text, value: node[field], type: "number", dataName, onChange: (input) => {
      const value = Number(input.value);
      if (input.value !== "" && Number.isFinite(value)) updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { [field]: value } }, showError);
    } });
  }
  appendLabelControl(root, selected, node, canvasController);
}

function appendChoice(root, { text, value, choices, dataName, onChange, allowNull = false }) {
  const label = document.createElement("label");
  label.textContent = text;
  const select = document.createElement("select");
  select.dataset[dataName] = "";
  if (allowNull) {
    const option = document.createElement("option"); option.value = ""; option.textContent = "未指定"; select.append(option);
  }
  for (const choice of choices) {
    const option = document.createElement("option");
    option.value = String(choice.id);
    option.textContent = choice.name;
    select.append(option);
  }
  select.value = String(value ?? "");
  select.addEventListener("change", () => onChange(select));
  label.append(select);
  root.append(label);
}

function appendMemberControls(root, selected, member, canvasController, materials, sections, draft, labels) {
  const nodes = draft.nodes.map((node) => ({ id: node.client_key, name: labels.label("GEOMETRY_NODE", node.client_key) }));
  for (const [field, text, dataName] of [["start_node_client_key", "起点", "propertyStartNode"], ["end_node_client_key", "终点", "propertyEndNode"]]) {
    appendChoice(root, { text, value: member[field], choices: nodes, dataName, allowNull: true, onChange: (select) => {
      updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { [field]: select.value || null } });
    } });
  }
  appendChoice(root, { text: "材料", value: member.material_id, choices: materials, dataName: "propertyMaterial", allowNull: true, onChange: (select) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { material_id: select.value ? Number(select.value) : null } });
  } });
  appendChoice(root, { text: "截面", value: member.section_id, choices: sections, dataName: "propertySection", allowNull: true, onChange: (select) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { section_id: select.value ? Number(select.value) : null } });
  } });
  appendLabelControl(root, selected, member, canvasController);
  const label = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.dataset.propertyActive = "";
  checkbox.checked = member.is_active;
  checkbox.addEventListener("change", () => updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { is_active: checkbox.checked } }));
  label.append(checkbox, " 参与分析");
  root.append(label);
  const material = materials.find(item => item.id === member.material_id);
  const section = sections.find(item => item.id === member.section_id);
  const details = document.createElement("details");
  details.className = "ux-advanced-properties";
  const summary = document.createElement("summary"); summary.textContent = "专业参数"; details.append(summary);
  const values = [
    ["弹性模量 E", material?.E_MPa, "MPa"], ["密度", material?.density_g_per_mm3, "g/mm³"],
    ["截面面积 A", section?.A_mm2, "mm²"], ["Ix", section?.Ix_mm4, "mm⁴"], ["Iy", section?.Iy_mm4, "mm⁴"],
  ];
  for (const [name, value, unit] of values) { const line = document.createElement("p"); line.textContent = `${name}：${value == null ? "未提供" : `${value} ${unit}`}`; details.append(line); }
  root.append(details);
}

function appendConnectionDetails(root, connection, labels, selected, canvasController, draft, editable, showError) {
  const node = document.createElement("p");
  node.dataset.propertyConnectionNodeText = "";
  node.textContent = connection.geometry_node_client_key ? labels.label("GEOMETRY_NODE", connection.geometry_node_client_key) : "位置节点：未指定";
  const members = document.createElement("p");
  members.dataset.propertyConnectionMembers = "";
  members.textContent = `参与构件：${connection.participating_member_client_keys.map((key) => key ? labels.label("PHYSICAL_MEMBER", key) : "未指定").join("、") || "无"}`;
  root.append(node, members);
  if (!editable) return;
  const nodeChoices = draft.nodes.map((item) => ({ id: item.client_key, name: labels.label("GEOMETRY_NODE", item.client_key) }));
  appendChoice(root, { text: "位置节点", value: connection.geometry_node_client_key, choices: nodeChoices, dataName: "propertyConnectionNode", allowNull: true, onChange: (select) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { geometry_node_client_key: select.value || null } });
  } });
  connection.participating_member_client_keys.forEach((key, index) => {
    const choices = draft.physical_members.map((item) => ({ id: item.client_key, name: labels.label("PHYSICAL_MEMBER", item.client_key) }));
    appendChoice(root, { text: `参与构件 ${index + 1}`, value: key, choices, dataName: "propertyParticipant", allowNull: true, onChange: (select) => {
      const current = canvasController.getState().draft.connections.find((item) => item.client_key === selected.clientKey);
      if (!current) return;
      const slots = [...current.participating_member_client_keys];
      const chosen = select.value || null;
      if (chosen && slots.some((value, slotIndex) => slotIndex !== index && value === chosen)) {
        select.value = slots[index] || "";
        showError({ code: "EDITOR_DUPLICATE_PARTICIPANT", message: "该构件已在此连接中参与，请选择其他构件。" });
        return;
      }
      slots[index] = chosen;
      updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { participating_member_client_keys: slots } });
    } });
    root.lastElementChild.querySelector("select").dataset.propertyParticipant = String(index);
  });
}

function supportValue(support) {
  return support.support_type === "ROLLER" ? `ROLLER_${support.restrained_axis}` : "PINNED";
}

function appendSupportControls(root, selected, support, canvasController, draft, labels) {
  appendChoice(root, { text: "作用位置", value: support.target_connection_client_key, choices: draft.connections.map((item) => ({ id: item.client_key, name: labels.label("CONNECTION", item.client_key) })), dataName: "propertySupportTarget", allowNull: true, onChange: (select) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { target_connection_client_key: select.value || null } });
  } });
  const label = document.createElement("label");
  label.textContent = "支座类型";
  const select = document.createElement("select");
  select.dataset.propertySupportType = "";
  for (const [value, text] of [["PINNED", "铰支座"], ["ROLLER_X", "滚动支座（限制 X）"], ["ROLLER_Y", "滚动支座（限制 Y）"]]) {
    const option = document.createElement("option"); option.value = value; option.textContent = text; select.append(option);
  }
  select.value = supportValue(support);
  select.addEventListener("change", () => {
    const changes = select.value === "PINNED" ? { support_type: "PINNED", restrained_axis: null } : { support_type: "ROLLER", restrained_axis: select.value.at(-1) };
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes });
  });
  label.append(select); root.append(label);
}

function appendLoadControls(root, selected, load, canvasController, draft, labels) {
  appendChoice(root, { text: "作用位置", value: load.target_connection_client_key, choices: draft.connections.map((item) => ({ id: item.client_key, name: labels.label("CONNECTION", item.client_key) })), dataName: "propertyLoadTarget", allowNull: true, onChange: (select) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { target_connection_client_key: select.value || null } });
  } });
  for (const [field, text, dataName] of [["fx_N", "Fx (N)", "propertyFx"], ["fy_N", "Fy (N)", "propertyFy"]]) {
    labeledInput(root, { text, value: load[field], type: "number", dataName, onChange: (input) => {
      const value = Number(input.value);
      if (input.value !== "" && Number.isFinite(value)) updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { [field]: value } });
    } });
  }
  appendLabelControl(root, selected, load, canvasController);
}

function deleteSelection(canvasController, showError) {
  const state = canvasController.getState();
  const targets = state.selectedObjects?.length ? state.selectedObjects : state.selectedObject ? [state.selectedObject] : [];
  if (!targets.length) return;
  try {
    const next = applyWorkspaceEditorAction(state, { type: "DELETE_OBJECTS", targets });
    const newlyIncomplete = [
      ...next.draft.physical_members.filter((item) => {
        const prior = state.draft.physical_members.find((old) => old.client_key === item.client_key);
        return prior && ((prior.start_node_client_key && !item.start_node_client_key) || (prior.end_node_client_key && !item.end_node_client_key));
      }),
      ...next.draft.connections.filter((item) => {
        const prior = state.draft.connections.find((old) => old.client_key === item.client_key);
        return prior && ((prior.geometry_node_client_key && !item.geometry_node_client_key) || item.participating_member_client_keys.some((key, index) => key === null && prior.participating_member_client_keys[index]));
      }),
      ...next.draft.supports.filter((item) => state.draft.supports.some((old) => old.client_key === item.client_key && hasTargetLocation(state.draft, old.target_connection_client_key) && !hasTargetLocation(next.draft, item.target_connection_client_key))),
      ...next.draft.node_loads.filter((item) => state.draft.node_loads.some((old) => old.client_key === item.client_key && hasTargetLocation(state.draft, old.target_connection_client_key) && !hasTargetLocation(next.draft, item.target_connection_client_key))),
    ];
    if (newlyIncomplete.length && !window.confirm(`删除后，${newlyIncomplete.length} 个其他对象需要重新指定。这些对象不会被删除。继续？`)) return;
    deleteFeedback = newlyIncomplete.length ? `已删除所选对象；${newlyIncomplete.length} 个对象需要重新指定，且不会被删除。` : "已删除所选对象。";
    canvasController.replaceState({ ...next, selectedObject: null, selectedObjects: [], focusedObject: null }, true);
    document.getElementById("workspace-save-status").textContent = next.dirty ? "未保存修改：有" : "未保存修改：无";
  } catch (error) {
    if (error instanceof EditorActionError) {
      showError({ code: error.code, message: "所选对象无法删除，请重新选择。" });
      return;
    }
    throw error;
  }
}

function appendDelete(root, selected, canvasController, showError) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.propertyDelete = "";
  button.textContent = "删除所选对象";
  button.addEventListener("click", () => deleteSelection(canvasController, showError));
  root.append(button);
}

export function bindPropertyPanel({ root, canvasController, materials = [], sections = [], showError = () => {} }) {
  canvasController.setPropertiesHandler(() => {
    root.scrollIntoView({ block: "nearest", behavior: "smooth" });
    (root.querySelector("input, select, [data-property-delete]") || root).focus({ preventScroll: true });
  });
  document.addEventListener("keydown", (event) => {
    if (!["Delete", "Backspace"].includes(event.key) || event.defaultPrevented) return;
    const target = event.target;
    if (target?.closest?.("input, textarea, select, [contenteditable], [role='textbox']")) return;
    const state = canvasController.getState();
    if (state.readOnly || root.closest("#workspace-root")?.dataset.uxStage !== "build" || !(state.selectedObjects?.length || state.selectedObject)) return;
    event.preventDefault();
    deleteSelection(canvasController, showError);
  });
  const render = (state) => {
    if (propertyEditing.has(canvasController)) return;
    root.replaceChildren();
    if (deleteFeedback) { const feedback = document.createElement("p"); feedback.dataset.deleteFeedback = ""; feedback.setAttribute("role", "status"); feedback.textContent = deleteFeedback; root.append(feedback); }
    const labels = createStudentLabelResolver(state.draft);
    const inventory = document.createElement("section"); inventory.dataset.draftObjectList = "";
    const inventoryHeading = document.createElement("h3"); inventoryHeading.textContent = "草稿对象"; inventory.append(inventoryHeading);
    for (const [kind, definition] of Object.entries(OBJECTS)) for (const record of state.draft[definition.collection] || []) {
      const button = document.createElement("button"); button.type = "button";
      button.dataset.draftObjectKind = kind; button.dataset.draftObjectKey = record.client_key;
      button.textContent = labels.label(kind, record.client_key);
      if (kind === "PHYSICAL_MEMBER" && (!record.start_node_client_key || !record.end_node_client_key || !record.material_id || !record.section_id) ||
          kind === "CONNECTION" && (!record.geometry_node_client_key || record.participating_member_client_keys.includes(null)) ||
          ["SUPPORT", "NODE_LOAD"].includes(kind) && !hasTargetLocation(state.draft, record.target_connection_client_key)) button.textContent += " · ⚠ 尚未完整 · 未指定";
      button.addEventListener("click", () => { const target = { kind, clientKey: record.client_key }; const current = canvasController.getState(); canvasController.replaceState({ ...current, selectedObject: target, selectedObjects: [target], focusedObject: target }); });
      inventory.append(button);
    }
    root.append(inventory);
    const current = selectedRecord(state);
    const parent = root.closest("#workspace-workflow-panel");
    const workspace = root.closest("#workspace-root");
    if (workspace) workspace.dataset.uxSelection = current ? "object" : "none";
    const title = parent?.querySelector("[data-ux-panel-title]");
    const guidance = parent?.querySelector("[data-ux-panel-guidance]");
    if (workspace?.dataset.uxStage === "build") {
      if (title) title.textContent = current ? "当前对象" : "当前任务";
      if (guidance) guidance.textContent = current ? "选中的对象会在画布中高亮。" : state.draft.nodes.length ? "选择工具后，点击画布或已有对象继续。" : "在画布点一下，放置第一个节点。";
    }
    const heading = (text) => { const element = document.createElement("h3"); element.textContent = text; root.append(element); };
    const note = (text) => { const element = document.createElement("p"); element.textContent = text; root.append(element); };
    heading("这是什么");
    if (!current) { note("这里是你的结构草稿。"); heading("可以做什么"); note("选择左侧工具，在画布放置节点、连接构件。"); heading("下一步"); note(state.draft.nodes.length ? "继续建立结构，或选择对象修改。" : "先放置第一个节点。"); return; }
    if ((state.selectedObjects?.length || 0) > 1) note(`已选择 ${state.selectedObjects.length} 个对象；下方显示最后选中的对象。删除会作用于全部所选对象。`);
    const identity = document.createElement("p"); identity.dataset.propertyIdentity = ""; identity.textContent = labels.label(current.selected.kind, current.selected.clientKey); root.append(identity);
    const kind = current.selected.kind;
    if (kind === "GEOMETRY_NODE") note(`结构上的一个位置：X ${current.record.x_mm} mm，Y ${current.record.y_mm} mm。`);
    if (kind === "PHYSICAL_MEMBER") { const from = current.record.start_node_client_key ? labels.label("GEOMETRY_NODE", current.record.start_node_client_key) : "未指定"; const to = current.record.end_node_client_key ? labels.label("GEOMETRY_NODE", current.record.end_node_client_key) : "未指定"; note(`从 ${from} 到 ${to}。材料与截面决定它的基本刚度。`); }
    if (kind === "CONNECTION") note("这里明确连接参与的构件；构件相交不等于连接。");
    if (kind === "SUPPORT") { note(current.record.support_type === "PINNED" ? "铰支座限制水平和竖直位移。" : `滚动支座限制 ${current.record.restrained_axis} 方向位移。`); if (!hasTargetLocation(state.draft, current.record.target_connection_client_key)) note("作用位置未指定，请重新指定连接或修复该连接的位置节点。"); }
    if (kind === "NODE_LOAD") { note(`作用在连接点上的荷载：水平 ${current.record.fx_N} N，竖直 ${current.record.fy_N} N。正负号表示方向。`); if (!hasTargetLocation(state.draft, current.record.target_connection_client_key)) note("作用位置未指定，请重新指定连接或修复该连接的位置节点。"); }
    heading("可以做什么");
    if (current.selected.kind === "CONNECTION") appendConnectionDetails(root, current.record, labels, current.selected, canvasController, state.draft, !state.readOnly, showError);
    if (!state.readOnly) {
      if (kind === "GEOMETRY_NODE") appendNodeControls(root, current.selected, current.record, canvasController, showError);
      if (kind === "PHYSICAL_MEMBER") appendMemberControls(root, current.selected, current.record, canvasController, materials, sections, state.draft, labels);
      if (kind === "SUPPORT") appendSupportControls(root, current.selected, current.record, canvasController, state.draft, labels);
      if (kind === "NODE_LOAD") appendLoadControls(root, current.selected, current.record, canvasController, state.draft, labels);
      appendDelete(root, current.selected, canvasController, showError);
    }
    heading("下一步");
    note(kind === "GEOMETRY_NODE" ? "继续放置节点，再用构件连接。" : kind === "PHYSICAL_MEMBER" ? "检查材料与截面，必要时调整。" : kind === "CONNECTION" ? "需要时添加支座或荷载。" : "保存模型，再运行检查。 ");
  };
  canvasController.subscribeStateChange(render);
  render(canvasController.getState());
}
