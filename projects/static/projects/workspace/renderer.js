const SVG_NS = "http://www.w3.org/2000/svg";
import { GRID_SPACING } from "./canvas-interaction.js";
import { createStudentLabelResolver } from "./labels.js";

function element(name, attributes = {}) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  return node;
}

function selectable(kind, key, label, uiState) {
  const stateKind = { GeometryNode: "GEOMETRY_NODE", PhysicalMember: "PHYSICAL_MEMBER", Connection: "CONNECTION", Support: "SUPPORT", NodeLoad: "NODE_LOAD" }[kind];
  const selected = [kind, stateKind].includes(uiState.selectedObject?.kind) && uiState.selectedObject?.clientKey === key;
  const focused = [kind, stateKind].includes(uiState.focusedObject?.kind) && uiState.focusedObject?.clientKey === key;
  return element("g", {
    "data-object-kind": kind,
    "data-client-key": key,
    tabindex: "0",
    role: "button",
    "aria-label": label,
    "data-selected": selected ? "true" : "false",
    "data-focused": focused ? "true" : "false",
  });
}

function ordered(items) {
  return [...items].sort((left, right) => left.client_key.localeCompare(right.client_key));
}

function pointMap(nodes) {
  return new Map(nodes.map((node) => [node.client_key, { x: node.x_mm, y: node.y_mm }]));
}

function viewTransform(view = {}) {
  const { a = 1, b = 0, c = 0, d = -1, e = 0, f = 0 } = view;
  return `matrix(${a} ${b} ${c} ${d} ${e} ${f})`;
}

function position(connection, nodePositions) {
  return nodePositions.get(connection.geometry_node_client_key);
}

export function workspaceWorldBounds(draft) {
  const points = (draft.nodes || []).filter((node) => Number.isFinite(node.x_mm) && Number.isFinite(node.y_mm));
  if (!points.length) return null;
  return { minX: Math.min(...points.map((node) => node.x_mm)), minY: Math.min(...points.map((node) => node.y_mm)), maxX: Math.max(...points.map((node) => node.x_mm)), maxY: Math.max(...points.map((node) => node.y_mm)) };
}

function gridLayer() {
  const grid = element("g", { "data-canvas-grid": "true", "pointer-events": "none", stroke: "#d9e3f0", "stroke-width": 1 });
  for (let coordinate = -10000; coordinate <= 10000; coordinate += GRID_SPACING) {
    grid.append(element("line", { x1: coordinate, y1: -10000, x2: coordinate, y2: 10000 }));
    grid.append(element("line", { x1: -10000, y1: coordinate, x2: 10000, y2: coordinate }));
  }
  grid.append(element("path", { d: "M -30 0 L 30 0 M 0 -30 L 0 30", stroke: "#7c8ba1", "stroke-width": 2 }));
  const origin = element("text", { x: 12, y: -12, fill: "#536274", "font-size": 24 }); origin.textContent = "(0,0)"; grid.append(origin);
  return grid;
}

function orientationLayer() {
  const group = element("g", { "data-canvas-orientation": "true", "pointer-events": "none", fill: "#34445c", stroke: "#34445c", "stroke-width": 3 });
  group.append(element("path", { d: "M 42 552 L 92 552 M 42 552 L 42 502" }));
  const label = element("text", { x: 98, y: 556, "font-size": 20, stroke: "none" }); label.textContent = "+X → +Y ↑"; group.append(label);
  return group;
}

function cadPresentationLayer(cad = {}) {
  const group = element("g", { "data-cad-presentation": "true", "pointer-events": "none" });
  if (cad.preview?.start && cad.preview?.end) {
    group.append(element("line", {
      "data-cad-member-preview": "true",
      x1: cad.preview.start.x,
      y1: cad.preview.start.y,
      x2: cad.preview.end.x,
      y2: cad.preview.end.y,
      stroke: "#7c3aed",
      "stroke-width": 5,
      "stroke-dasharray": "14 8",
      opacity: .85,
      "pointer-events": "none",
    }));
  }
  const feedback = cad.snapFeedback;
  if (feedback?.point && ["NODE", "INT", "GRID"].includes(feedback.snapType)) {
    const marker = element("g", {
      "data-cad-snap-marker": "true",
      "data-snap-type": feedback.snapType,
      transform: `translate(${feedback.point.x} ${feedback.point.y})`,
      "pointer-events": "none",
    });
    const shape = feedback.snapType === "NODE"
      ? element("circle", { cx: 0, cy: 0, r: 13, fill: "none", stroke: "#0759c7", "stroke-width": 4 })
      : feedback.snapType === "INT"
        ? element("path", { d: "M -12 -12 L 12 12 M -12 12 L 12 -12", stroke: "#b54708", "stroke-width": 4 })
        : element("rect", { x: -10, y: -10, width: 20, height: 20, fill: "none", stroke: "#196127", "stroke-width": 4 });
    const label = element("text", { x: 16, y: -16, fill: "#172033", "font-size": 22, "font-weight": 700, transform: "scale(1 -1)" });
    label.textContent = feedback.snapType;
    marker.append(shape, label);
    group.append(marker);
  }
  return group;
}

export function renderCadPresentation(svg, cad = {}) {
  const current = svg.querySelector("[data-cad-presentation]");
  const next = cadPresentationLayer(cad);
  if (current) current.replaceWith(next);
  else svg.querySelector("[data-world-layer]")?.append(next);
}

export function renderSnapIndicator(indicator, resolution) {
  const snapType = ["NODE", "INT", "GRID"].includes(resolution?.snapType) ? resolution.snapType : null;
  indicator.textContent = snapType ? `SNAP: ${snapType}` : "SNAP: 无";
  indicator.dataset.snapType = snapType || "";
}

export function predictionSelectableObject(selection) {
  if (!selection || !["CONNECTION", "PHYSICAL_MEMBER"].includes(selection.kind) || typeof selection.clientKey !== "string") return null;
  return Object.freeze({ kind: selection.kind, clientKey: selection.clientKey });
}

export function renderWorkspace(svg, draft, uiState = {}) {
  const nodes = ordered(draft.nodes || []);
  const members = ordered(draft.physical_members || []);
  const connections = ordered(draft.connections || []);
  const loads = ordered(draft.node_loads || []);
  const supports = ordered(draft.supports || []);
  const nodePositions = pointMap(nodes);
  const connectionByKey = new Map(connections.map((connection) => [connection.client_key, connection]));
  const labels = createStudentLabelResolver(draft);
  const grid = gridLayer();
  const layers = [element("g", { "data-render-layer": "members" }), element("g", { "data-render-layer": "supports-loads" }), element("g", { "data-render-layer": "nodes-connections" })];

  for (const member of members) {
    const start = nodePositions.get(member.start_node_client_key);
    const end = nodePositions.get(member.end_node_client_key);
    if (!start || !end) continue;
    const result = uiState.resultOverlay?.[member.client_key];
    const group = selectable("PhysicalMember", member.client_key, `${labels.label("PHYSICAL_MEMBER", member.client_key)}${result ? `，结果：${result.label}` : ""}`, uiState);
    group.dataset.resultState = result?.state || "";
    group.append(element("line", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, stroke: result?.color || "currentColor", "stroke-width": 8, "stroke-dasharray": result?.dash || "none" }));
    layers[0].append(group);
  }

  for (const support of supports) {
    const connection = connectionByKey.get(support.target_connection_client_key);
    const target = connection && position(connection, nodePositions);
    if (!target) continue;
    const label = support.support_type === "ROLLER" ? `${labels.label("SUPPORT", support.client_key)}，滚动支座，限制 ${support.restrained_axis}` : `${labels.label("SUPPORT", support.client_key)}，铰支座`;
    const group = selectable("Support", support.client_key, label, uiState);
    group.append(element("path", { d: `M ${target.x - 18} ${target.y + 22} L ${target.x + 18} ${target.y + 22} L ${target.x} ${target.y}`, fill: "none", stroke: "currentColor", "stroke-width": 3 }));
    if (support.support_type === "ROLLER") group.append(element("line", support.restrained_axis === "X" ? { x1: target.x - 13, y1: target.y + 30, x2: target.x + 13, y2: target.y + 30, stroke: "currentColor", "stroke-width": 3 } : { x1: target.x, y1: target.y + 27, x2: target.x, y2: target.y + 39, stroke: "currentColor", "stroke-width": 3 }));
    layers[1].append(group);
  }

  for (const load of loads) {
    const connection = connectionByKey.get(load.target_connection_client_key);
    const target = connection && position(connection, nodePositions);
    if (!target) continue;
    const group = selectable("NodeLoad", load.client_key, labels.label("NODE_LOAD", load.client_key), uiState);
    const dx = load.fx_N === 0 ? 0 : (load.fx_N > 0 ? 30 : -30);
    const dy = load.fy_N === 0 ? 0 : (load.fy_N > 0 ? -30 : 30);
    if (dx === 0 && dy === 0) group.append(element("circle", { cx: target.x, cy: target.y, r: 10, fill: "none", stroke: "currentColor", "stroke-width": 3 }));
    else group.append(element("line", { x1: target.x - dx, y1: target.y - dy, x2: target.x, y2: target.y, stroke: "currentColor", "stroke-width": 3, "marker-end": "url(#workspace-load-arrow)" }));
    layers[1].append(group);
  }

  for (const node of nodes) {
    const point = nodePositions.get(node.client_key);
    const group = selectable("GeometryNode", node.client_key, labels.label("GEOMETRY_NODE", node.client_key), uiState);
    group.append(element("circle", { cx: point.x, cy: point.y, r: 7, fill: "currentColor" }));
    layers[2].append(group);
  }
  for (const connection of connections) {
    const target = position(connection, nodePositions);
    if (!target) continue;
    const group = selectable("Connection", connection.client_key, labels.label("CONNECTION", connection.client_key), uiState);
    group.append(element("rect", { x: target.x - 5, y: target.y - 5, width: 10, height: 10, fill: "white", stroke: "currentColor", "stroke-width": 2 }));
    layers[2].append(group);
  }

  const defs = element("defs");
  const marker = element("marker", { id: "workspace-load-arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto" });
  marker.append(element("path", { d: "M 0 0 L 8 4 L 0 8 z", fill: "currentColor" }));
  defs.append(marker);
  const world = element("g", { "data-world-layer": "true", transform: viewTransform(uiState.viewTransform) });
  if (uiState.cad?.gridVisible !== false) world.append(grid);
  world.append(...layers, cadPresentationLayer(uiState.cad));
  svg.replaceChildren(defs, world, orientationLayer());
}
