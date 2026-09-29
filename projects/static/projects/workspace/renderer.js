const SVG_NS = "http://www.w3.org/2000/svg";
import { GRID_SPACING, visibleGridLevels } from "./grid.js";
import { createStudentLabelResolver } from "./labels.js";
import { structuralSymbolDefs, renderNode, renderMember, renderConnection, renderSupport, renderLoad } from "./structural-symbols.js";
import { candidateMembersAtNode } from "./joint-candidates.js";

function element(name, attributes = {}) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  return node;
}

function selectable(kind, key, label, uiState) {
  const stateKind = { GeometryNode: "GEOMETRY_NODE", PhysicalMember: "PHYSICAL_MEMBER", Connection: "CONNECTION", Support: "SUPPORT", NodeLoad: "NODE_LOAD" }[kind];
  const selected = (uiState.selectedObjects || (uiState.selectedObject ? [uiState.selectedObject] : [])).some((item) => [kind, stateKind].includes(item.kind) && item.clientKey === key);
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

function screenUnit(svg, uiState) {
  const viewBox = svg.viewBox.baseVal;
  const viewportScale = Math.min(svg.clientWidth / (viewBox.width || 1000), svg.clientHeight / (viewBox.height || 600));
  return 1 / Math.max(0.001, viewportScale * Math.abs(uiState.viewTransform?.a ?? 1));
}

function position(connection, nodePositions) {
  return nodePositions.get(connection.geometry_node_client_key);
}

export function workspaceWorldBounds(draft) {
  const points = (draft.nodes || []).filter((node) => Number.isFinite(node.x_mm) && Number.isFinite(node.y_mm));
  if (!points.length) return null;
  return { minX: Math.min(...points.map((node) => node.x_mm)), minY: Math.min(...points.map((node) => node.y_mm)), maxX: Math.max(...points.map((node) => node.x_mm)), maxY: Math.max(...points.map((node) => node.y_mm)) };
}

function gridLayer(unit) {
  const levels = visibleGridLevels(1 / unit);
  const grid = element("g", { "data-canvas-grid": "true", "data-grid-visible-levels": [levels.minor && "minor", levels.medium && "medium", "major"].filter(Boolean).join(" "), "pointer-events": "none" });
  const defs = element("defs");
  const pattern = (name, spacing, color, inner = null) => {
    const tile = element("pattern", { id: `workspace-grid-${name}`, "data-grid-level": name, patternUnits: "userSpaceOnUse", x: 0, y: 0, width: spacing, height: spacing });
    if (inner) tile.append(element("rect", { x: 0, y: 0, width: spacing, height: spacing, fill: `url(#workspace-grid-${inner})` }));
    tile.append(element("path", { d: `M 0 0 H ${spacing} M 0 0 V ${spacing}`, fill: "none", stroke: color, "stroke-width": unit }));
    return tile;
  };
  defs.append(pattern("minor", GRID_SPACING, "#f1f5fa"));
  defs.append(pattern("medium", 10 * GRID_SPACING, "#e4ebf4", levels.minor ? "minor" : null));
  defs.append(pattern("major", 100 * GRID_SPACING, "#cbd8e9", levels.medium ? "medium" : null));
  grid.append(defs, element("rect", { x: -10000, y: -10000, width: 20000, height: 20000, fill: "url(#workspace-grid-major)" }));
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

function cadPresentationLayer(cad = {}, unit = 1) {
  const group = element("g", { "data-cad-presentation": "true", "pointer-events": "none" });
  if (cad.loadPreview?.point) {
    const preview = element("g", { "data-cad-load-preview": "true", opacity: .65, "pointer-events": "none" });
    preview.append(renderLoad(cad.loadPreview, cad.loadPreview.point, unit, { preview: true }));
    group.append(preview);
  }
  if (cad.gripPreview) {
    for (const member of cad.gripPreview.members || []) group.append(element("line", {
      "data-cad-grip-preview": "member", x1: member.start.x, y1: member.start.y,
      x2: member.end.x, y2: member.end.y, stroke: "#d97706", "stroke-width": 6,
      "stroke-dasharray": "10 5", "pointer-events": "none",
    }));
    group.append(element("circle", { "data-cad-grip-preview": "node", cx: cad.gripPreview.point.x,
      cy: cad.gripPreview.point.y, r: 9, fill: "#f59e0b", "pointer-events": "none" }));
  }
  if (cad.trackingGuide?.start && cad.trackingGuide?.end) group.append(element("line", {
    "data-cad-tracking-guide": "true",
    x1: cad.trackingGuide.start.x, y1: cad.trackingGuide.start.y,
    x2: cad.trackingGuide.end.x, y2: cad.trackingGuide.end.y,
    stroke: "#0f766e", "stroke-width": 2, "stroke-dasharray": "8 5", "pointer-events": "none",
  }));
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
    label.textContent = feedback.snapType === "NODE" ? `○ ${feedback.studentLabel || "节点"}` : feedback.snapType === "INT" ? "× 交点" : "□ 网格";
    const tooltip = element("title");
    tooltip.textContent = feedback.unconnectedIntersection ? "这里有构件交叉，但尚未建立连接。" : label.textContent;
    marker.append(shape, label, tooltip);
    group.append(marker);
  }
  return group;
}

export function renderCadPresentation(svg, cad = {}, uiState = {}) {
  const current = svg.querySelector("[data-cad-presentation]");
  const next = cadPresentationLayer(cad, screenUnit(svg, uiState));
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
  const v2 = draft.schema_version === "physical-draft-v2";
  const unit = screenUnit(svg, uiState);
  const nodes = ordered(draft.nodes || []);
  const members = ordered(draft.physical_members || []);
  const connections = v2 ? [] : ordered(draft.connections || []);
  const loads = ordered(draft.node_loads || []);
  const supports = ordered(draft.supports || []);
  const nodePositions = pointMap(nodes);
  const connectionByKey = new Map(connections.map((connection) => [connection.client_key, connection]));
  const labels = createStudentLabelResolver(draft);
  const grid = gridLayer(unit);
  const layers = [element("g", { "data-render-layer": "members" }), element("g", { "data-render-layer": "supports" }), element("g", { "data-render-layer": "connections" }), element("g", { "data-render-layer": "nodes" }), element("g", { "data-render-layer": "loads" })];

  for (const member of members) {
    const start = nodePositions.get(member.start_node_client_key);
    const end = nodePositions.get(member.end_node_client_key);
    if (!start || !end) continue;
    const result = uiState.resultOverlay?.[member.client_key];
    const group = selectable("PhysicalMember", member.client_key, `${labels.label("PHYSICAL_MEMBER", member.client_key)}${result ? `，结果：${result.label}` : ""}`, uiState);
    group.dataset.resultState = result?.state || "";
    group.append(renderMember(member, start, end, unit, { result }));
    layers[0].append(group);
  }

  for (const support of supports) {
    const connection = connectionByKey.get(support.target_connection_client_key);
    const target = v2 ? nodePositions.get(support.target_node_client_key) : connection && position(connection, nodePositions);
    if (!target) continue;
    const label = support.support_type === "ROLLER" ? `${labels.label("SUPPORT", support.client_key)}，滚动支座，限制 ${support.restrained_axis}` : `${labels.label("SUPPORT", support.client_key)}，铰支座`;
    const group = selectable("Support", support.client_key, label, uiState);
    group.append(renderSupport(support, target, unit));
    layers[1].append(group);
  }

  for (const load of loads) {
    const connection = connectionByKey.get(load.target_connection_client_key);
    const target = v2 ? nodePositions.get(load.target_node_client_key) : connection && position(connection, nodePositions);
    if (!target) continue;
    const group = selectable("NodeLoad", load.client_key, labels.label("NODE_LOAD", load.client_key), uiState);
    group.append(renderLoad(load, target, unit, { showLabels: 1 / unit >= 0.3 }));
    layers[4].append(group);
  }

  for (const connection of connections) {
    const target = position(connection, nodePositions);
    if (!target) continue;
    const group = selectable("Connection", connection.client_key, labels.label("CONNECTION", connection.client_key), uiState);
    group.append(renderConnection(connection, target, unit));
    layers[2].append(group);
  }
  for (const node of nodes) {
    const point = nodePositions.get(node.client_key);
    const group = selectable("GeometryNode", node.client_key, labels.label("GEOMETRY_NODE", node.client_key), uiState);
    group.append(renderNode(node, point, unit));
    if (v2 && nodes.some((other) => other.client_key !== node.client_key && other.x_mm === node.x_mm && other.y_mm === node.y_mm)) {
      group.dataset.legacyDuplicateIdentity = "true";
      group.append(element("circle", { cx: point.x, cy: point.y, r: 15 * unit, fill: "none", stroke: "#b45309", "stroke-width": 2 * unit, "stroke-dasharray": `${3 * unit} ${2 * unit}`, "pointer-events": "none" }));
      const warning = element("title"); warning.textContent = "这里有多个位置相同但彼此不连接的旧模型节点。"; group.append(warning);
    }
    if (v2) {
      const unjoined = candidateMembersAtNode(draft, node).filter((memberKey) => {
        const member = members.find((row) => row.client_key === memberKey);
        return ![member.start_node_client_key, member.end_node_client_key].includes(node.client_key)
          && !(draft.member_joint_incidences || []).some((row) => row.member_client_key === memberKey && row.node_client_key === node.client_key);
      });
      if (unjoined.length) {
        group.dataset.legacyUnjoinedPass = unjoined.join(" ");
        group.append(element("path", { d: `M ${point.x + 12 * unit} ${point.y - 12 * unit} l ${8 * unit} ${-8 * unit} m ${-8 * unit} 0 l ${8 * unit} ${8 * unit}`, fill: "none", stroke: "#b45309", "stroke-width": 2 * unit, "pointer-events": "none" }));
        const warning = element("title"); warning.textContent = `旧模型中构件 ${unjoined.join("、")} 穿过此节点，但彼此不连接。`; group.append(warning);
      }
    }
    layers[3].append(group);
  }
  if (uiState.cad?.activeCommand === "SELECT" && !uiState.readOnly) for (const item of uiState.selectedObjects || []) {
    if (item.kind !== "GEOMETRY_NODE") continue;
    const point = nodePositions.get(item.clientKey); if (!point) continue;
    layers[3].append(element("rect", { "data-cad-node-grip": item.clientKey,
      x: point.x - 5 * unit, y: point.y - 5 * unit, width: 10 * unit, height: 10 * unit,
      fill: "#f59e0b", stroke: "#854d0e", "stroke-width": 1.5 * unit, cursor: "move" }));
  }

  const defs = structuralSymbolDefs();
  const world = element("g", { "data-world-layer": "true", transform: viewTransform(uiState.viewTransform) });
  if (uiState.cad?.gridVisible !== false) world.append(grid);
  world.append(...layers, cadPresentationLayer(uiState.cad, unit));
  svg.replaceChildren(defs, world, orientationLayer());
}
