import { EditorActionError } from "./editor.js";
import { worldPointFromEvent } from "./canvas-interaction.js";
import { applyWorkspaceEditorAction } from "./state.js";

const TOOL_LABELS = Object.freeze({
  SELECT: "选择",
  NODE: "节点",
  MEMBER: "构件",
  CONNECTION: "连接",
  SUPPORT: "支座",
  LOAD: "荷载",
});

const OBJECT_KINDS = Object.freeze({
  GeometryNode: "GEOMETRY_NODE",
  Connection: "CONNECTION",
});

function selectedTarget(event) {
  const group = event.composedPath?.().find((element) => element?.matches?.("[data-object-kind]"));
  const kind = OBJECT_KINDS[group?.dataset.objectKind];
  return kind && group?.dataset.clientKey ? { kind, clientKey: group.dataset.clientKey } : null;
}

function nextKey(items, prefix) {
  let index = 1;
  const keys = new Set(items.map((item) => item.client_key));
  while (keys.has(`${prefix}-${index}`)) index += 1;
  return `${prefix}-${index}`;
}

function membersAtNode(draft, nodeKey) {
  return draft.physical_members
    .filter((member) => member.start_node_client_key === nodeKey || member.end_node_client_key === nodeKey)
    .map((member) => member.client_key)
    .sort();
}

function nodeTarget(draft, target) {
  if (target?.kind === "GEOMETRY_NODE") return target;
  if (target?.kind !== "CONNECTION") return null;
  const connection = draft.connections.find((item) => item.client_key === target.clientKey);
  return connection ? { kind: "GEOMETRY_NODE", clientKey: connection.geometry_node_client_key } : null;
}

function updateUi(root, tool, memberStart) {
  for (const button of root.querySelectorAll("[data-workspace-tool]")) {
    const active = button.dataset.workspaceTool === tool;
    button.dataset.active = active ? "true" : "false";
    button.setAttribute("aria-pressed", active ? "true" : "false");
  }
  const instruction = root.querySelector("[data-modeling-instruction]");
  if (instruction) instruction.textContent = memberStart ? "请选择构件的终点节点。" : `${TOOL_LABELS[tool]}工具已启用。`;
}

export function bindModelingInteractions({ root, svg, canvasController, showError, readOnly }) {
  if (readOnly) return Object.freeze({ getTool: () => "SELECT" });
  let tool = "SELECT";
  let memberStart = null;
  const apply = (action) => {
    try {
      canvasController.replaceState(applyWorkspaceEditorAction(canvasController.getState(), action));
      root.querySelector("#workspace-save-status").textContent = "未保存修改：有";
    } catch (error) {
      if (error instanceof EditorActionError) showError({ code: error.code, message: "当前工具目标不满足建模条件。" });
      else throw error;
    }
  };
  const chooseTool = (nextTool) => {
    tool = nextTool;
    memberStart = null;
    updateUi(root, tool, memberStart);
  };

  for (const button of root.querySelectorAll("[data-workspace-tool]")) {
    button.addEventListener("click", () => chooseTool(button.dataset.workspaceTool));
  }
  const handleCanvasClick = (event) => {
    const current = canvasController.getState();
    const target = selectedTarget(event);
    if (tool === "SELECT") return;
    if (tool === "NODE") {
      if (target) return;
      const resolved = worldPointFromEvent(svg, event);
      const point = resolved && { x: Math.round(resolved.x), y: Math.round(resolved.y) };
      if (!point) return;
      apply({ type: "CREATE_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } });
      return;
    }
    if (tool === "MEMBER") {
      const node = nodeTarget(current.draft, target);
      if (!node) return;
      if (!memberStart) {
        memberStart = node.clientKey;
        updateUi(root, tool, memberStart);
        return;
      }
      if (memberStart === node.clientKey) return;
      const exemplar = current.draft.physical_members[0];
      if (!exemplar) {
        showError({ code: "MEMBER_PROPERTIES_REQUIRED", message: "请先在已有构件上确定材料和截面后再创建构件。" });
        return;
      }
      apply({ type: "CREATE_MEMBER", member: { client_key: nextKey(current.draft.physical_members, "member"), start_node_client_key: memberStart, end_node_client_key: node.clientKey, material_id: exemplar.material_id, section_id: exemplar.section_id, label: "", is_active: true } });
      memberStart = null;
      updateUi(root, tool, memberStart);
      return;
    }
    if (tool === "CONNECTION") {
      const node = nodeTarget(current.draft, target);
      if (!node) return;
      const participants = membersAtNode(current.draft, node.clientKey);
      if (!participants.length) {
        showError({ code: "CONNECTION_MEMBER_REQUIRED", message: "请在已有构件端点创建连接。" });
        return;
      }
      apply({ type: "CREATE_CONNECTION", connection: { client_key: nextKey(current.draft.connections, "connection"), geometry_node_client_key: node.clientKey, participating_member_client_keys: participants } });
      return;
    }
    if (target?.kind !== "CONNECTION") return;
    if (tool === "SUPPORT") apply({ type: "CREATE_SUPPORT", support: { client_key: nextKey(current.draft.supports, "support"), target_connection_client_key: target.clientKey, support_type: "PINNED", restrained_axis: null } });
    if (tool === "LOAD") apply({ type: "CREATE_NODE_LOAD", nodeLoad: { client_key: nextKey(current.draft.node_loads, "load"), target_connection_client_key: target.clientKey, fx_N: 0, fy_N: -100, label: "" } });
  };
  canvasController.setCanvasClickHandler(handleCanvasClick);
  updateUi(root, tool, memberStart);
  return Object.freeze({ getTool: () => tool });
}
