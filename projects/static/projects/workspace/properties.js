import { applyWorkspaceEditorAction } from "./state.js";

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

function updateState(canvasController, action) {
  const next = applyWorkspaceEditorAction(canvasController.getState(), action);
  canvasController.replaceState(next);
  document.getElementById("workspace-save-status").textContent = "未保存修改：有";
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
  for (const [field, text] of [["fx_N", "Fx (N)"], ["fy_N", "Fy (N)"]]) {
    const label = document.createElement("label"); label.textContent = text;
    const input = document.createElement("input"); input.type = "number"; input.step = "any";
    input.dataset[field === "fx_N" ? "propertyFx" : "propertyFy"] = "";
    input.value = String(load[field]);
    input.addEventListener("change", () => {
      if (input.value.trim() === "") return;
      const value = Number(input.value);
      if (!Number.isFinite(value)) return;
      updateState(canvasController, { type: "UPDATE_OBJECT", target: selected, changes: { [field]: value } });
    });
    label.append(input); root.append(label);
  }
}

export function bindPropertyPanel({ root, canvasController }) {
  const render = (state) => {
    root.replaceChildren();
    const current = selectedRecord(state);
    if (!current) { const hint = document.createElement("p"); hint.textContent = "请选择对象查看属性。"; root.append(hint); return; }
    const identity = document.createElement("p"); identity.dataset.propertyIdentity = ""; identity.textContent = `${current.definition.label} ${current.record.client_key}`; root.append(identity);
    if (state.readOnly) return;
    if (current.selected.kind === "SUPPORT") appendSupportControls(root, current.selected, current.record, canvasController);
    if (current.selected.kind === "NODE_LOAD") appendLoadControls(root, current.selected, current.record, canvasController);
  };
  canvasController.setStateChangeHandler(render);
  render(canvasController.getState());
}
