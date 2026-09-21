import { EditorActionError } from "./editor.js";
import { worldPointFromEvent } from "./canvas-interaction.js";
import { parseCadInput } from "./cad-input.js";
import { resolvePointerPoint } from "./geometry.js";
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

function segmentIntersection(left, right) {
  const denominator = (left.end.x - left.start.x) * (right.end.y - right.start.y) - (left.end.y - left.start.y) * (right.end.x - right.start.x);
  if (Math.abs(denominator) < 1e-12) return null;
  const dx = right.start.x - left.start.x;
  const dy = right.start.y - left.start.y;
  const t = (dx * (right.end.y - right.start.y) - dy * (right.end.x - right.start.x)) / denominator;
  const u = (dx * (left.end.y - left.start.y) - dy * (left.end.x - left.start.x)) / denominator;
  if (t < 0 || t > 1 || u < 0 || u > 1) return null;
  return { x: left.start.x + t * (left.end.x - left.start.x), y: left.start.y + t * (left.end.y - left.start.y) };
}

function drawingCandidates(draft) {
  const nodes = new Map(draft.nodes.map((node) => [node.client_key, node]));
  const nodeCandidates = draft.nodes.map((node) => ({
    kind: "NODE",
    canonicalKey: `NODE:${node.client_key}`,
    worldPoint: { x: node.x_mm, y: node.y_mm },
  }));
  const segments = draft.physical_members.flatMap((member) => {
    const start = nodes.get(member.start_node_client_key);
    const end = nodes.get(member.end_node_client_key);
    return start && end ? [{ key: member.client_key, start: { x: start.x_mm, y: start.y_mm }, end: { x: end.x_mm, y: end.y_mm } }] : [];
  });
  const intersections = [];
  for (let left = 0; left < segments.length; left += 1) {
    for (let right = left + 1; right < segments.length; right += 1) {
      const point = segmentIntersection(segments[left], segments[right]);
      if (!point) continue;
      const keys = [segments[left].key, segments[right].key].sort();
      intersections.push({ kind: "INTERSECTION", canonicalKey: `INTERSECTION:${keys[0]}|${keys[1]}`, worldPoint: point });
    }
  }
  return [...nodeCandidates, ...intersections];
}

function cadState(state) {
  return state.cad || { ortho: false, gridSnap: true, gridVisible: true, activeCommand: "SELECT", origin: null };
}

function cadStatus(root, cad, resolution = null) {
  const indicator = root.querySelector("#workspace-snap-indicator");
  if (!indicator) return;
  indicator.textContent = `ORTHO: ${cad.ortho ? "开" : "关"} · SNAP: ${cad.gridSnap ? "开" : "关"} · 捕捉: ${resolution?.snapType || "无"}`;
  indicator.dataset.snapType = resolution?.snapType || "";
}

export function bindModelingInteractions({ root, svg, canvasController, showError, readOnly }) {
  if (readOnly) return Object.freeze({ getTool: () => "SELECT" });
  let tool = "SELECT";
  let memberStart = null;
  const apply = (action, cadChanges = null) => {
    try {
      const edited = applyWorkspaceEditorAction(canvasController.getState(), action);
      canvasController.replaceState(cadChanges ? { ...edited, cad: Object.freeze({ ...cadState(edited), ...cadChanges }) } : edited);
      root.querySelector("#workspace-save-status").textContent = "未保存修改：有";
    } catch (error) {
      if (error instanceof EditorActionError) showError({ code: error.code, message: "当前工具目标不满足建模条件。" });
      else throw error;
    }
  };
  const chooseTool = (nextTool) => {
    tool = nextTool;
    memberStart = null;
    const current = canvasController.getState();
    canvasController.replaceState({ ...current, cad: Object.freeze({ ...cadState(current), activeCommand: nextTool }) });
    updateUi(root, tool, memberStart);
  };

  for (const button of root.querySelectorAll("[data-workspace-tool]")) {
    button.addEventListener("click", () => chooseTool(button.dataset.workspaceTool));
  }
  const orthoButton = root.querySelector("[data-cad-ortho]");
  const snapButton = root.querySelector("[data-cad-snap]");
  const commandInput = root.querySelector("[data-cad-command-input]");
  const toggleCad = (field, button) => {
    const current = canvasController.getState();
    const nextCad = Object.freeze({ ...cadState(current), [field]: !cadState(current)[field] });
    canvasController.replaceState({ ...current, cad: nextCad });
    button.setAttribute("aria-pressed", nextCad[field] ? "true" : "false");
    cadStatus(root, nextCad);
  };
  orthoButton?.addEventListener("click", () => toggleCad("ortho", orthoButton));
  snapButton?.addEventListener("click", () => toggleCad("gridSnap", snapButton));
  commandInput?.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      commandInput.value = "";
      const current = canvasController.getState();
      canvasController.replaceState({ ...current, cad: Object.freeze({ ...cadState(current), origin: null }) });
      return;
    }
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (tool !== "NODE") {
      showError({ code: "CAD_COMMAND_CONTEXT", message: "请先选择节点工具再输入坐标。" });
      return;
    }
    const current = canvasController.getState();
    const parsed = parseCadInput(commandInput.value, cadState(current).origin);
    if (!parsed.ok) {
      showError({ code: `CAD_INPUT_${parsed.code}`, message: "坐标格式无效，请输入 x,y、@dx,dy 或 长度<角度。" });
      return;
    }
    const point = resolvePointerPoint({
      worldPointer: parsed.point,
      screenPointer: parsed.point,
      candidates: [],
      viewTransform: current.viewTransform,
      origin: cadState(current).origin || parsed.point,
      ortho: false,
      gridEnabled: false,
      explicitNumeric: true,
    }).point;
    apply({ type: "CREATE_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } }, { origin: point });
    commandInput.value = "";
    cadStatus(root, cadState(canvasController.getState()));
  });
  const handleCanvasClick = (event) => {
    const current = canvasController.getState();
    const target = selectedTarget(event);
    if (tool === "SELECT") return;
    if (tool === "NODE") {
      if (target) return;
      const world = worldPointFromEvent(svg, event);
      const cad = cadState(current);
      const resolved = world && resolvePointerPoint({
        worldPointer: world,
        screenPointer: { x: event.clientX, y: event.clientY },
        candidates: cad.gridSnap ? drawingCandidates(current.draft) : [],
        viewTransform: current.viewTransform,
        origin: cad.origin || world,
        ortho: cad.ortho,
        gridEnabled: cad.gridSnap,
        explicitNumeric: false,
      });
      const point = resolved?.point && { x: Math.round(resolved.point.x * 1e9) / 1e9, y: Math.round(resolved.point.y * 1e9) / 1e9 };
      if (!point) return;
      if (resolved.candidateKey?.startsWith("NODE:")) {
        cadStatus(root, cad, resolved);
        return;
      }
      apply({ type: "CREATE_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } }, { origin: point });
      cadStatus(root, cadState(canvasController.getState()), resolved);
      return;
    }
    if (tool === "MEMBER") {
      const node = nodeTarget(current.draft, target) || nodeTarget(current.draft, current.selectedObject);
      if (!node) return;
      if (!memberStart) {
        memberStart = node.clientKey;
        updateUi(root, tool, memberStart);
        return;
      }
      if (memberStart === node.clientKey) return;
      const materialId = Number(root.querySelector("[data-member-material]")?.value);
      const sectionId = Number(root.querySelector("[data-member-section]")?.value);
      if (!Number.isInteger(materialId) || materialId <= 0 || !Number.isInteger(sectionId) || sectionId <= 0) {
        showError({ code: "MEMBER_PROPERTIES_REQUIRED", message: "请选择新构件使用的材料和截面。" });
        return;
      }
      apply({ type: "CREATE_MEMBER", member: { client_key: nextKey(current.draft.physical_members, "member"), start_node_client_key: memberStart, end_node_client_key: node.clientKey, material_id: materialId, section_id: sectionId, label: "", is_active: true } });
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
  canvasController.setPointerMoveHandler((world, state, screen) => {
    if (!world) return;
    root.querySelector("#workspace-pointer-x").textContent = `X: ${Math.round(world.x)} mm`;
    root.querySelector("#workspace-pointer-y").textContent = `Y: ${Math.round(world.y)} mm`;
    const cad = cadState(state);
    const resolution = resolvePointerPoint({
      worldPointer: world,
      screenPointer: screen,
      candidates: cad.gridSnap ? drawingCandidates(state.draft) : [],
      viewTransform: state.viewTransform,
      origin: cad.origin || world,
      ortho: cad.ortho,
      gridEnabled: cad.gridSnap,
      explicitNumeric: false,
    });
    cadStatus(root, cad, resolution);
  });
  updateUi(root, tool, memberStart);
  cadStatus(root, cadState(canvasController.getState()));
  return Object.freeze({ getTool: () => tool });
}
