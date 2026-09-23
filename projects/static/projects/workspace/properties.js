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

function selectedRecord(state) {
  const selected = state.selectedObject;
  const definition = OBJECTS[selected?.kind];
  if (!definition) return null;
  const record = state.draft[definition.collection]?.find((item) => item.client_key === selected.clientKey);
  return record ? { definition, record, selected } : null;
}

function updateState(canvasController, action, notifyPanel = false) {
  const next = applyWorkspaceEditorAction(canvasController.getState(), action);
  canvasController.replaceState(next, notifyPanel);
  document.getElementById("workspace-save-status").textContent = "未保存修改：有";
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

function appendNodeControls(root, selected, node, canvasController) {
  for (const [field, text, dataName] of [["x_mm", "X（mm）", "propertyX"], ["y_mm", "Y（mm）", "propertyY"]]) {
    labeledInput(root, { text, value: node[field], type: "number", dataName, onChange: (input) => {
      const value = Number(input.value);
      if (Number.isFinite(value)) updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { [field]: value } });
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
      if (Number.isFinite(value)) updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { [field]: value } });
    } });
  }
  appendLabelControl(root, selected, load, canvasController);
}

function appendDelete(root, selected, canvasController, showError) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.propertyDelete = "";
  button.textContent = "删除对象";
  button.addEventListener("click", () => {
    try {
      updateState(canvasController, { type: "DELETE_OBJECT", target: selected }, true);
    } catch (error) {
      if (error instanceof EditorActionError && error.code === "EDITOR_DEPENDENCY_CONFLICT") {
        showError({ code: error.code, message: "请先删除或调整依赖该对象的构件、连接、支座或荷载。" });
        return;
      }
      throw error;
    }
  });
  root.append(button);
}

export function bindPropertyPanel({ root, canvasController, materials = [], sections = [], showError = () => {} }) {
  const render = (state) => {
    root.replaceChildren();
    const current = selectedRecord(state);
    if (!current) { const hint = document.createElement("p"); hint.textContent = "请选择对象查看属性。"; root.append(hint); return; }
    const labels = createStudentLabelResolver(state.draft);
    const identity = document.createElement("p"); identity.dataset.propertyIdentity = ""; identity.textContent = labels.label(current.selected.kind, current.selected.clientKey); root.append(identity);
    if (current.selected.kind === "CONNECTION") appendConnectionDetails(root, current.record, labels);
    if (state.readOnly) return;
    if (current.selected.kind === "GEOMETRY_NODE") appendNodeControls(root, current.selected, current.record, canvasController);
    if (current.selected.kind === "PHYSICAL_MEMBER") appendMemberControls(root, current.selected, current.record, canvasController, materials, sections);
    if (current.selected.kind === "SUPPORT") appendSupportControls(root, current.selected, current.record, canvasController);
    if (current.selected.kind === "NODE_LOAD") appendLoadControls(root, current.selected, current.record, canvasController);
    appendDelete(root, current.selected, canvasController, showError);
  };
  canvasController.setStateChangeHandler(render);
  render(canvasController.getState());
}
