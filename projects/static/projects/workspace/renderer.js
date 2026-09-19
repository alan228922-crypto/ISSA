const SVG_NS = "http://www.w3.org/2000/svg";

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
  const layers = [element("g", { "data-render-layer": "members" }), element("g", { "data-render-layer": "supports-loads" }), element("g", { "data-render-layer": "nodes-connections" })];

  for (const member of members) {
    const start = nodePositions.get(member.start_node_client_key);
    const end = nodePositions.get(member.end_node_client_key);
    if (!start || !end) continue;
    const result = uiState.resultOverlay?.[member.client_key];
    const group = selectable("PhysicalMember", member.client_key, `构件 ${member.client_key}${result ? `，结果：${result.label}` : ""}`, uiState);
    group.dataset.resultState = result?.state || "";
    group.append(element("line", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, stroke: result?.color || "currentColor", "stroke-width": 8, "stroke-dasharray": result?.dash || "none" }));
    layers[0].append(group);
  }

  for (const support of supports) {
    const connection = connectionByKey.get(support.target_connection_client_key);
    const target = connection && position(connection, nodePositions);
    if (!target) continue;
    const label = support.support_type === "ROLLER" ? `滚动支座 ${support.restrained_axis} ${support.target_connection_client_key}` : `铰支座 ${support.target_connection_client_key}`;
    const group = selectable("Support", support.client_key, label, uiState);
    group.append(element("path", { d: `M ${target.x - 18} ${target.y + 22} L ${target.x + 18} ${target.y + 22} L ${target.x} ${target.y}`, fill: "none", stroke: "currentColor", "stroke-width": 3 }));
    layers[1].append(group);
  }

  for (const load of loads) {
    const connection = connectionByKey.get(load.target_connection_client_key);
    const target = connection && position(connection, nodePositions);
    if (!target) continue;
    const group = selectable("NodeLoad", load.client_key, `节点荷载 ${load.client_key}`, uiState);
    const dx = load.fx_N === 0 ? 0 : (load.fx_N > 0 ? 30 : -30);
    const dy = load.fy_N === 0 ? 0 : (load.fy_N > 0 ? -30 : 30);
    if (dx === 0 && dy === 0) group.append(element("circle", { cx: target.x, cy: target.y, r: 10, fill: "none", stroke: "currentColor", "stroke-width": 3 }));
    else group.append(element("line", { x1: target.x - dx, y1: target.y - dy, x2: target.x, y2: target.y, stroke: "currentColor", "stroke-width": 3, "marker-end": "url(#workspace-load-arrow)" }));
    layers[1].append(group);
  }

  for (const node of nodes) {
    const point = nodePositions.get(node.client_key);
    const group = selectable("GeometryNode", node.client_key, `节点 ${node.client_key}`, uiState);
    group.append(element("circle", { cx: point.x, cy: point.y, r: 7, fill: "currentColor" }));
    layers[2].append(group);
  }
  for (const connection of connections) {
    const target = position(connection, nodePositions);
    if (!target) continue;
    const group = selectable("Connection", connection.client_key, `连接 ${connection.client_key}`, uiState);
    group.append(element("rect", { x: target.x - 5, y: target.y - 5, width: 10, height: 10, fill: "white", stroke: "currentColor", "stroke-width": 2 }));
    layers[2].append(group);
  }

  const defs = element("defs");
  const marker = element("marker", { id: "workspace-load-arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto" });
  marker.append(element("path", { d: "M 0 0 L 8 4 L 0 8 z", fill: "currentColor" }));
  defs.append(marker);
  const world = element("g", { "data-world-layer": "true", transform: viewTransform(uiState.viewTransform) });
  world.append(...layers);
  svg.replaceChildren(defs, world);
}
