import { EditorActionError } from "./editor.js";
import { pickAt, renderedObjectsFromSvg, worldPointFromEvent } from "./canvas-interaction.js";
import { parseCadInput } from "./cad-input.js";
import { transition } from "./cad-state.js";
import { resolvePointerPoint } from "./geometry.js";
import { renderCadPresentation } from "./renderer.js";
import { applyWorkspaceEditorAction } from "./state.js";

const TOOL_INSTRUCTIONS = Object.freeze({ SELECT: "点击结构查看或修改", NODE: "在画布放置节点；交叉处放置节点即形成桁架铰接", MEMBER: "选择起点，再选择终点", SUPPORT: "选择构件节点放置支座", LOAD: "选择构件节点施加荷载" });
const COMPLETED = Object.freeze({ CREATE_NODE: "已放置节点", PLACE_JOINT_NODE: "已放置节点", CREATE_MEMBER: "已添加构件", CREATE_SUPPORT_AT_NODE: "已放置支座", CREATE_NODE_LOAD_AT_NODE: "已施加荷载" });
const OBJECT_KINDS = Object.freeze({ GeometryNode: "GEOMETRY_NODE", Connection: "CONNECTION" });

function selectedTarget(event) {
  const group = event.composedPath?.().find((element) => element?.matches?.("[data-object-kind]")) || event.target?.closest?.("[data-object-kind]");
  const kind = OBJECT_KINDS[group?.dataset.objectKind];
  return kind && group?.dataset.clientKey ? { kind, clientKey: group.dataset.clientKey } : null;
}

function targetAtClick(event, svg, allowedKinds) {
  const direct = selectedTarget(event);
  if (direct && allowedKinds.includes(direct.kind)) return direct;
  return pickAt({ x: event.clientX, y: event.clientY }, renderedObjectsFromSvg(svg).filter(object => allowedKinds.includes(object.kind)));
}

function nextKey(items, prefix) {
  let index = 1; const keys = new Set(items.map((item) => item.client_key));
  while (keys.has(`${prefix}-${index}`)) index += 1;
  return `${prefix}-${index}`;
}

function nodeTarget(draft, target) {
  if (target?.kind === "GEOMETRY_NODE") return target;
  if (target?.kind !== "CONNECTION") return null;
  const connection = draft.connections.find((item) => item.client_key === target.clientKey);
  return connection ? { kind: "GEOMETRY_NODE", clientKey: connection.geometry_node_client_key } : null;
}

function updateUi(root, tool, memberStart, contextualInstruction = null) {
  root.dataset.uxTool = tool;
  for (const button of root.querySelectorAll("[data-workspace-tool]")) {
    const active = button.dataset.workspaceTool === tool;
    button.dataset.active = active ? "true" : "false"; button.setAttribute("aria-pressed", active ? "true" : "false");
  }
  const instruction = root.querySelector("[data-modeling-instruction]");
  if (instruction) instruction.textContent = memberStart ? "请选择构件的终点节点。按 Esc 可取消。" : contextualInstruction || TOOL_INSTRUCTIONS[tool];
  for (const input of root.querySelectorAll("[data-cad-distance], [data-cad-angle]")) input.disabled = !(tool === "MEMBER" && memberStart);
}

function segmentIntersection(left, right) {
  const denominator = (left.end.x - left.start.x) * (right.end.y - right.start.y) - (left.end.y - left.start.y) * (right.end.x - right.start.x);
  if (Math.abs(denominator) < 1e-12) return null;
  const dx = right.start.x - left.start.x; const dy = right.start.y - left.start.y;
  const t = (dx * (right.end.y - right.start.y) - dy * (right.end.x - right.start.x)) / denominator;
  const u = (dx * (left.end.y - left.start.y) - dy * (left.end.x - left.start.x)) / denominator;
  if (t < 0 || t > 1 || u < 0 || u > 1) return null;
  return { x: left.start.x + t * (left.end.x - left.start.x), y: left.start.y + t * (left.end.y - left.start.y) };
}

function drawingCandidates(draft) {
  const nodes = new Map(draft.nodes.map((node) => [node.client_key, node]));
  const candidates = draft.nodes.map((node) => ({ kind: "NODE", canonicalKey: `NODE:${node.client_key}`, worldPoint: { x: node.x_mm, y: node.y_mm } }));
  const segments = draft.physical_members.flatMap((member) => {
    const start = nodes.get(member.start_node_client_key); const end = nodes.get(member.end_node_client_key);
    return start && end ? [{ key: member.client_key, start: { x: start.x_mm, y: start.y_mm }, end: { x: end.x_mm, y: end.y_mm } }] : [];
  });
  for (let left = 0; left < segments.length; left += 1) for (let right = left + 1; right < segments.length; right += 1) {
    const point = segmentIntersection(segments[left], segments[right]); if (!point) continue;
    const keys = [segments[left].key, segments[right].key].sort();
    candidates.push({ kind: "INTERSECTION", canonicalKey: `INTERSECTION:${keys[0]}|${keys[1]}`, worldPoint: point });
  }
  return candidates;
}

function cadState(state) { return state.cad || { ortho: false, gridSnap: true, gridVisible: true, activeCommand: "SELECT", origin: null }; }
function localScreenPoint(svg, point) {
  const matrix = svg.getScreenCTM?.();
  if (!matrix) return point;
  const local = new DOMPoint(point.x, point.y).matrixTransform(matrix.inverse());
  return { x: local.x, y: local.y };
}
function cadStatus(root, cad, resolution = null) {
  const indicator = root.querySelector("#workspace-snap-indicator"); if (!indicator) return;
  indicator.textContent = `ORTHO: ${cad.ortho ? "开" : "关"} · SNAP: ${cad.gridSnap ? "开" : "关"} (Grid) · 对象捕捉: 开 · 当前: ${resolution?.snapType || "无"}`;
  indicator.dataset.snapType = resolution?.snapType || "";
}

export function bindModelingInteractions({ root, svg, canvasController, showError, readOnly }) {
  if (readOnly) return Object.freeze({ getTool: () => "SELECT" });
  let tool = "SELECT"; let memberStart = null; let contextualInstruction = null; let commandState = { state: "SELECTING", fieldIndex: null };
  const distanceInput = root.querySelector("[data-cad-distance]"); const angleInput = root.querySelector("[data-cad-angle]");
  const commandInput = root.querySelector("[data-cad-command-input]");
  const transientCad = (changes, notify = false) => {
    const current = canvasController.getState();
    const next = { ...current, cad: Object.freeze({ ...cadState(current), ...changes }) };
    canvasController.replaceState(next, notify, false);
    renderCadPresentation(svg, next.cad);
  };
  const clearInputs = () => {
    if (commandInput) commandInput.value = "";
    if (distanceInput) distanceInput.value = "";
    if (angleInput) angleInput.value = "";
  };
  const cancelCommand = () => {
    memberStart = null;
    contextualInstruction = null;
    commandState = transition(commandState, { type: "ESC" });
    tool = "SELECT";
    clearInputs();
    transientCad({ activeCommand: "SELECT", origin: null, preview: null, snapFeedback: null });
    updateUi(root, tool, memberStart, contextualInstruction);
    cadStatus(root, cadState(canvasController.getState()));
  };
  const apply = (action, cadChanges = null) => {
    try {
      const previous = canvasController.getState();
      const edited = applyWorkspaceEditorAction(previous, action);
      if (edited.draft === previous.draft) {
        root.querySelector("[data-modeling-instruction]").textContent = "此处节点已连接构件，无需重复放置。";
        return true;
      }
      canvasController.replaceState(cadChanges ? { ...edited, cad: Object.freeze({ ...cadState(edited), ...cadChanges }) } : edited);
      contextualInstruction = null;
      root.querySelector("#workspace-save-status").textContent = "未保存修改：有";
      if (COMPLETED[action.type]) root.querySelector("[data-modeling-instruction]").textContent = COMPLETED[action.type];
      return true;
    } catch (error) {
      if (error instanceof EditorActionError) {
        const messages = { NODE_NOT_ON_MEMBER: "此节点未连接构件；请先绘制构件。", MULTIPLE_JOINTS_AT_NODE: "此节点有多个旧连接，无法确定支座或荷载目标；请先整理模型。" };
        showError({ code: error.code, message: messages[error.code] || "当前工具目标不满足建模条件。" }); return false;
      }
      throw error;
    }
  };
  const memberOrigin = () => { const node = canvasController.getState().draft.nodes.find((item) => item.client_key === memberStart); return node && { x: node.x_mm, y: node.y_mm }; };
  const updateDynamics = (point) => {
    const origin = memberOrigin(); if (!origin || !point) return;
    const dx = point.x - origin.x; const dy = point.y - origin.y;
    root.querySelector("#workspace-delta-length").textContent = `ΔL: ${Math.round(Math.hypot(dx, dy) * 1000) / 1000} mm`;
    root.querySelector("#workspace-angle").textContent = `Angle: ${Math.round(Math.atan2(dy, dx) * 180 / Math.PI * 1000) / 1000}°`;
  };
  const memberProfile = () => {
    const materialId = Number(root.querySelector("[data-member-material]")?.value); const sectionId = Number(root.querySelector("[data-member-section]")?.value);
    if (!Number.isInteger(materialId) || materialId <= 0 || !Number.isInteger(sectionId) || sectionId <= 0) { showError({ code: "MEMBER_PROPERTIES_REQUIRED", message: "请选择新构件使用的材料和截面。" }); return null; }
    return { materialId, sectionId };
  };
  const completeMemberAt = (point) => {
    const profile = memberProfile(); if (!memberStart || !profile) return false;
    let current = canvasController.getState(); let endpoint = current.draft.nodes.find((node) => Math.abs(node.x_mm - point.x) < 1e-9 && Math.abs(node.y_mm - point.y) < 1e-9);
    if (!endpoint) { endpoint = { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" }; apply({ type: "PLACE_JOINT_NODE", node: endpoint }, { origin: point }); current = canvasController.getState(); }
    if (endpoint.client_key === memberStart) return false;
    apply({ type: "CREATE_MEMBER", member: { client_key: nextKey(current.draft.physical_members, "member"), start_node_client_key: memberStart, end_node_client_key: endpoint.client_key, material_id: profile.materialId, section_id: profile.sectionId, label: "", is_active: true } }, { origin: point, preview: null, snapFeedback: null });
    updateDynamics(point); memberStart = null; commandState = transition(commandState, { type: "ENTER", valid: true, point }); distanceInput.value = ""; angleInput.value = ""; updateUi(root, tool, memberStart); return true;
  };
  const chooseTool = (nextTool) => {
    tool = nextTool; memberStart = null; contextualInstruction = null; clearInputs(); commandState = transition(commandState, { type: "SELECT_TOOL", tool: nextTool });
    const current = canvasController.getState(); canvasController.replaceState({ ...current, cad: Object.freeze({ ...cadState(current), activeCommand: nextTool, preview: null, snapFeedback: null }) }); updateUi(root, tool, memberStart, contextualInstruction);
  };
  for (const button of root.querySelectorAll("[data-workspace-tool]")) button.addEventListener("click", () => chooseTool(button.dataset.workspaceTool));
  const orthoButton = root.querySelector("[data-cad-ortho]"); const snapButton = root.querySelector("[data-cad-snap]");
  const toggleCad = (field, button) => { const current = canvasController.getState(); const nextCad = Object.freeze({ ...cadState(current), [field]: !cadState(current)[field] }); canvasController.replaceState({ ...current, cad: nextCad }); button.setAttribute("aria-pressed", nextCad[field] ? "true" : "false"); cadStatus(root, nextCad); };
  orthoButton?.addEventListener("click", () => toggleCad("ortho", orthoButton)); snapButton?.addEventListener("click", () => toggleCad("gridSnap", snapButton));
  const dynamicPoint = () => { const origin = memberOrigin(); const distance = Number(distanceInput?.value); const angle = Number(angleInput?.value); if (!origin || !Number.isFinite(distance) || distance <= 0 || !Number.isFinite(angle)) return null; const radians = angle * Math.PI / 180; return { x: origin.x + distance * Math.cos(radians), y: origin.y + distance * Math.sin(radians) }; };
  for (const [input, field] of [[distanceInput, "DISTANCE"], [angleInput, "ANGLE"]]) input?.addEventListener("input", () => { commandState = transition(commandState, { type: "INPUT_CHANGE", mode: "DYNAMIC", field, value: input.value }); updateDynamics(dynamicPoint()); });
  for (const [input, field] of [[distanceInput, "DISTANCE"], [angleInput, "ANGLE"]]) input?.addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      commandState = transition(commandState, { type: "INPUT_CHANGE", mode: "DYNAMIC", field, value: input.value });
      commandState = transition(commandState, { type: "TAB" });
      if (input === angleInput && !event.shiftKey) { event.preventDefault(); distanceInput.focus(); }
      return;
    }
    if (event.key === "Enter") { event.preventDefault(); const point = dynamicPoint(); if (!point || !completeMemberAt(point)) showError({ code: "CAD_INPUT_MALFORMED", message: "请输入大于 0 的距离和有效角度。" }); }
  });
  commandInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return; event.preventDefault();
    if (tool !== "NODE" && !(tool === "MEMBER" && memberStart)) { showError({ code: "CAD_COMMAND_CONTEXT", message: "请先选择节点工具，或先选择构件起点。" }); return; }
    const current = canvasController.getState(); const parsed = parseCadInput(commandInput.value, tool === "MEMBER" ? memberOrigin() : cadState(current).origin);
    if (!parsed.ok) { showError({ code: `CAD_INPUT_${parsed.code}`, message: "坐标格式无效，请输入 x,y、@dx,dy 或 长度<角度。" }); return; }
    const point = resolvePointerPoint({ worldPointer: parsed.point, screenPointer: parsed.point, candidates: [], viewTransform: current.viewTransform, origin: (tool === "MEMBER" ? memberOrigin() : cadState(current).origin) || parsed.point, ortho: false, gridEnabled: false, explicitNumeric: true }).point;
    if (tool === "MEMBER") completeMemberAt(point); else { apply({ type: "PLACE_JOINT_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } }, { origin: point }); commandState = transition(commandState, { type: "ENTER", valid: true, point }); }
    commandInput.value = ""; cadStatus(root, cadState(canvasController.getState()));
  });
  const handleCanvasClick = (event) => {
    if (root.dataset.uxStage !== "build") return;
    const current = canvasController.getState(); const target = targetAtClick(event, svg, ["GEOMETRY_NODE", "CONNECTION"]); if (tool === "SELECT") return;
    if (tool === "NODE") {
      if (target) {
        const node = nodeTarget(current.draft, target);
        if (node) apply({ type: "CONNECT_NODE", nodeClientKey: node.clientKey });
        return;
      }
      const world = worldPointFromEvent(svg, event); const cad = cadState(current);
      const resolved = world && resolvePointerPoint({ worldPointer: world, screenPointer: localScreenPoint(svg, { x: event.clientX, y: event.clientY }), candidates: drawingCandidates(current.draft), viewTransform: current.viewTransform, origin: cad.origin || world, ortho: cad.ortho, gridEnabled: cad.gridSnap, explicitNumeric: false });
      const point = resolved?.point && { x: Math.round(resolved.point.x * 1e9) / 1e9, y: Math.round(resolved.point.y * 1e9) / 1e9 }; if (!point) return;
      if (resolved.candidateKey?.startsWith("NODE:")) {
        apply({ type: "CONNECT_NODE", nodeClientKey: resolved.candidateKey.slice(5) });
        cadStatus(root, cad, resolved); return;
      }
      apply({ type: "PLACE_JOINT_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } }, { origin: point, preview: null, snapFeedback: null }); commandState = transition(commandState, { type: "POINTER_POINT", point }); cadStatus(root, cadState(canvasController.getState()), resolved); return;
    }
    if (tool === "MEMBER") {
      const node = nodeTarget(current.draft, target);
      if (!node && memberStart && ["DRAW_MEMBER_WAIT_END", "DYNAMIC_INPUT"].includes(commandState.state)) {
        const world = worldPointFromEvent(svg, event); const cad = cadState(current); if (!world) return;
        const resolved = resolvePointerPoint({ worldPointer: world, screenPointer: localScreenPoint(svg, { x: event.clientX, y: event.clientY }), candidates: drawingCandidates(current.draft), viewTransform: current.viewTransform, origin: memberOrigin(), ortho: cad.ortho, gridEnabled: cad.gridSnap, explicitNumeric: false });
        completeMemberAt({ x: Math.round(resolved.point.x * 1e9) / 1e9, y: Math.round(resolved.point.y * 1e9) / 1e9 }); cadStatus(root, cadState(canvasController.getState()), resolved); return;
      }
      if (!node) return;
      if (!memberStart) { memberStart = node.clientKey; const start = current.draft.nodes.find((item) => item.client_key === memberStart); commandState = transition(commandState, { type: "POINTER_POINT", point: { x: start.x_mm, y: start.y_mm } }); updateUi(root, tool, memberStart); return; }
      const endpoint = current.draft.nodes.find((item) => item.client_key === node.clientKey); completeMemberAt({ x: endpoint.x_mm, y: endpoint.y_mm }); return;
    }
    const node = nodeTarget(current.draft, target);
    if (!node) {
      contextualInstruction = "请点击构件节点放置支座或荷载；若尚无构件，请先绘制构件。";
      updateUi(root, tool, memberStart, contextualInstruction);
      return;
    }
    if (tool === "SUPPORT") {
      const clientKey = nextKey(current.draft.supports, "support");
      if (apply({ type: "CREATE_SUPPORT_AT_NODE", nodeClientKey: node.clientKey, support: { client_key: clientKey, support_type: "PINNED", restrained_axis: null } })) return { kind: "SUPPORT", clientKey };
    }
    if (tool === "LOAD") {
      const clientKey = nextKey(current.draft.node_loads, "load");
      if (apply({ type: "CREATE_NODE_LOAD_AT_NODE", nodeClientKey: node.clientKey, nodeLoad: { client_key: clientKey, fx_N: 0, fy_N: -100, label: "" } })) return { kind: "NODE_LOAD", clientKey };
    }
  };
  canvasController.setCanvasClickHandler(handleCanvasClick);
  const hasConnectionAt = (draft, point) => {
    const connectedNodes = new Set(draft.connections.map((connection) => connection.geometry_node_client_key));
    return draft.nodes.some((node) => connectedNodes.has(node.client_key) && Math.abs(node.x_mm - point.x) < 1e-9 && Math.abs(node.y_mm - point.y) < 1e-9);
  };
  canvasController.setPointerMoveHandler((world, state, screen) => {
    if (!world) return; root.querySelector("#workspace-pointer-x").textContent = `X: ${Math.round(world.x)} mm`; root.querySelector("#workspace-pointer-y").textContent = `Y: ${Math.round(world.y)} mm`;
    const cad = cadState(state); const resolution = resolvePointerPoint({ worldPointer: world, screenPointer: localScreenPoint(svg, screen), candidates: drawingCandidates(state.draft), viewTransform: state.viewTransform, origin: memberOrigin() || cad.origin || world, ortho: cad.ortho, gridEnabled: cad.gridSnap, explicitNumeric: false });
    const active = tool !== "SELECT";
    const unconnectedIntersection = resolution.snapType === "INT" && !hasConnectionAt(state.draft, resolution.point);
    transientCad({
      preview: memberStart ? { start: memberOrigin(), end: resolution.point } : null,
      snapFeedback: active && resolution.snapType ? { ...resolution, unconnectedIntersection } : null,
    });
    cadStatus(root, cadState(canvasController.getState()), resolution);
    updateUi(root, tool, memberStart, contextualInstruction);
    if (unconnectedIntersection && active && !contextualInstruction) root.querySelector("[data-modeling-instruction]").textContent = "这里有构件交叉，但尚未建立连接。";
    if (memberStart) updateDynamics(resolution.point);
  });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && tool !== "SELECT") { event.preventDefault(); event.stopPropagation(); cancelCommand(); } });
  svg.addEventListener("pointerleave", () => transientCad({ preview: null, snapFeedback: null }));
  updateUi(root, tool, memberStart, contextualInstruction); cadStatus(root, cadState(canvasController.getState())); return Object.freeze({ getTool: () => tool });
}
