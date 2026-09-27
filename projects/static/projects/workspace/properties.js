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

function appendChoice(root, { text, value, choices, dataName, onChange }) {
  const label = document.createElement("label");
  label.textContent = text;
  const select = document.createElement("select");
  select.dataset[dataName] = "";
  for (const choice of choices) {
    const option = document.createElement("option");
    option.value = String(choice.id);
    option.textContent = choice.name;
    select.append(option);
  }
  select.value = String(value);
  select.addEventListener("change", () => onChange(select));
  label.append(select);
  root.append(label);
}

function appendMemberControls(root, selected, member, canvasController, materials, sections) {
  appendChoice(root, { text: "材料", value: member.material_id, choices: materials, dataName: "propertyMaterial", onChange: (select) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { material_id: Number(select.value) } });
  } });
  appendChoice(root, { text: "截面", value: member.section_id, choices: sections, dataName: "propertySection", onChange: (select) => {
    updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { section_id: Number(select.value) } });
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

function appendConnectionDetails(root, connection, labels) {
  const node = document.createElement("p");
  node.dataset.propertyConnectionNode = "";
  node.textContent = `${labels.label("GEOMETRY_NODE", connection.geometry_node_client_key)}`;
  const members = document.createElement("p");
  members.dataset.propertyConnectionMembers = "";
  members.textContent = `参与构件：${connection.participating_member_client_keys.map((key) => labels.label("PHYSICAL_MEMBER", key)).join("、")}`;
  root.append(node, members);
}

function supportValue(support) {
  return support.support_type === "ROLLER" ? `ROLLER_${support.restrained_axis}` : "PINNED";
}

function appendSupportControls(root, selected, support, canvasController) {
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

function appendLoadControls(root, selected, load, canvasController) {
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
    canvasController.replaceState({ ...next, selectedObject: null, selectedObjects: [], focusedObject: null }, true);
    document.getElementById("workspace-save-status").textContent = next.dirty ? "未保存修改：有" : "未保存修改：无";
  } catch (error) {
    if (error instanceof EditorActionError) {
      showError({ code: error.code, message: error.code === "EDITOR_DEPENDENCY_CONFLICT" ? "无法删除：仍有构件、支座或荷载依赖所选对象。请同时选中依赖对象再删除。" : "所选对象无法删除，请重新选择。" });
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
    (root.querySelector("input, select, button") || root).focus({ preventScroll: true });
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
    const labels = createStudentLabelResolver(state.draft);
    const identity = document.createElement("p"); identity.dataset.propertyIdentity = ""; identity.textContent = labels.label(current.selected.kind, current.selected.clientKey); root.append(identity);
    const kind = current.selected.kind;
    if (kind === "GEOMETRY_NODE") note(`结构上的一个位置：X ${current.record.x_mm} mm，Y ${current.record.y_mm} mm。`);
    if (kind === "PHYSICAL_MEMBER") { const from = labels.label("GEOMETRY_NODE", current.record.start_node_client_key); const to = labels.label("GEOMETRY_NODE", current.record.end_node_client_key); note(`从 ${from} 到 ${to}。材料与截面决定它的基本刚度。`); }
    if (kind === "CONNECTION") note("这里明确连接参与的构件；构件相交不等于连接。");
    if (kind === "SUPPORT") note(current.record.support_type === "PINNED" ? "铰支座限制水平和竖直位移。" : `滚动支座限制 ${current.record.restrained_axis} 方向位移。`);
    if (kind === "NODE_LOAD") note(`作用在连接点上的荷载：水平 ${current.record.fx_N} N，竖直 ${current.record.fy_N} N。正负号表示方向。`);
    heading("可以做什么");
    if (current.selected.kind === "CONNECTION") appendConnectionDetails(root, current.record, labels);
    if (!state.readOnly) {
      if (kind === "GEOMETRY_NODE") appendNodeControls(root, current.selected, current.record, canvasController, showError);
      if (kind === "PHYSICAL_MEMBER") appendMemberControls(root, current.selected, current.record, canvasController, materials, sections);
      if (kind === "SUPPORT") appendSupportControls(root, current.selected, current.record, canvasController);
      if (kind === "NODE_LOAD") appendLoadControls(root, current.selected, current.record, canvasController);
      appendDelete(root, current.selected, canvasController, showError);
    }
    heading("下一步");
    note(kind === "GEOMETRY_NODE" ? "继续放置节点，再用构件连接。" : kind === "PHYSICAL_MEMBER" ? "检查材料与截面，必要时调整。" : kind === "CONNECTION" ? "需要时添加支座或荷载。" : "保存模型，再运行检查。 ");
  };
  canvasController.subscribeStateChange(render);
  render(canvasController.getState());
}
