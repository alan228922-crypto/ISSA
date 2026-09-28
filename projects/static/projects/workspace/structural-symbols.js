const SVG_NS = "http://www.w3.org/2000/svg";

function element(name, attributes = {}) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  return node;
}

function symbol(name, kind, attributes) {
  return element(name, { ...attributes, "data-structural-symbol": kind });
}

export function structuralSymbolDefs() {
  const defs = element("defs");
  const marker = element("marker", { id: "workspace-load-arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto" });
  marker.append(element("path", { d: "M 0 0 L 8 4 L 0 8 z", fill: "currentColor" }));
  defs.append(marker);
  const hatch = element("pattern", { id: "workspace-support-hatch", patternUnits: "userSpaceOnUse", width: 6, height: 6 });
  hatch.append(element("path", { d: "M -2 6 L 4 0 M 4 6 L 10 0", fill: "none", stroke: "#1f2937", "stroke-width": 1.2, "pointer-events": "none" }));
  defs.append(hatch);
  return defs;
}

export function renderMember(member, start, end, unit, visualState = {}) {
  const fragment = document.createDocumentFragment();
  const d = `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
  fragment.append(symbol("line", "member", { "data-member-body": "true", x1: start.x, y1: start.y, x2: end.x, y2: end.y, stroke: visualState.result?.color || "#1f2937", "stroke-width": 3 * unit, "stroke-dasharray": visualState.result?.dash || "none", "stroke-linecap": "round", "pointer-events": "none" }));
  fragment.append(element("path", { "data-hover-outline": "true", d, fill: "none", stroke: "#0f766e", "stroke-width": 8 * unit, "pointer-events": "none" }));
  fragment.append(element("path", { "data-selection-outline": "true", d, fill: "none", stroke: "#0759c7", "stroke-width": 11 * unit, "pointer-events": "none" }));
  fragment.append(element("path", { "data-symbol-hit": "true", d, fill: "none", stroke: "transparent", "stroke-width": 18 * unit, "pointer-events": "stroke" }));
  return fragment;
}

export function renderSupport(support, target, unit) {
  const fragment = document.createDocumentFragment();
  const roller = support.support_type === "ROLLER";
  const transform = `translate(${target.x} ${target.y}) scale(${unit})${roller && support.restrained_axis === "X" ? " rotate(-90)" : ""}`;
  const visual = element("g", { "data-structural-symbol": "support", transform, "pointer-events": "none" });
  visual.append(element("path", { "data-support-part": "triangle", d: "M 0 -16 L -15 -32 L 15 -32 Z", fill: "white", stroke: "#1f2937", "stroke-width": 2.2, "pointer-events": "none" }));
  if (roller) for (const x of [-8, 8]) visual.append(element("circle", { "data-support-part": "wheel", cx: x, cy: -38, r: 4, fill: "white", stroke: "#1f2937", "stroke-width": 2, "pointer-events": "none" }));
  const baseY = roller ? -45 : -36;
  visual.append(element("line", { "data-support-part": "base", x1: -22, y1: baseY, x2: 22, y2: baseY, stroke: "#1f2937", "stroke-width": 2.2, "pointer-events": "none" }));
  visual.append(element("rect", { "data-support-part": "hatch", x: -22, y: baseY - 8, width: 44, height: 8, fill: "url(#workspace-support-hatch)", "pointer-events": "none" }));
  fragment.append(visual);
  const hit = element("g", { transform, "data-symbol-hit": "true" });
  hit.append(element("rect", { x: -23, y: roller ? -54 : -45, width: 46, height: roller ? 39 : 30, fill: "transparent", "pointer-events": "all" }));
  fragment.append(hit);
  return fragment;
}

export function renderLoad(load, target, unit) {
  const dx = load.fx_N === 0 ? 0 : (load.fx_N > 0 ? 36 * unit : -36 * unit);
  const dy = load.fy_N === 0 ? 0 : (load.fy_N > 0 ? 36 * unit : -36 * unit);
  const length = Math.hypot(dx, dy);
  if (!length) return symbol("circle", "load", { cx: target.x, cy: target.y, r: 22 * unit, fill: "none", stroke: "currentColor", "stroke-width": 2.5 * unit });
  return symbol("line", "load", { x1: target.x - dx, y1: target.y - dy, x2: target.x - dx / length * 8 * unit, y2: target.y - dy / length * 8 * unit, stroke: "currentColor", "stroke-width": 2.5 * unit, "marker-end": "url(#workspace-load-arrow)" });
}

export function renderNode(node, point, unit) {
  const fragment = document.createDocumentFragment();
  fragment.append(symbol("circle", "node", { "data-node-body": "true", cx: point.x, cy: point.y, r: 7 * unit, fill: "white", stroke: "#1f2937", "stroke-width": 2 * unit, "pointer-events": "none" }));
  const circle = (radius) => `M ${point.x + radius * unit} ${point.y} a ${radius * unit} ${radius * unit} 0 1 0 ${-2 * radius * unit} 0 a ${radius * unit} ${radius * unit} 0 1 0 ${2 * radius * unit} 0`;
  fragment.append(element("path", { "data-hover-outline": "true", d: circle(10), fill: "none", stroke: "#0f766e", "stroke-width": 2 * unit, "pointer-events": "none" }));
  fragment.append(element("path", { "data-selection-outline": "true", d: circle(12), fill: "none", stroke: "#0759c7", "stroke-width": 2.5 * unit, "pointer-events": "none" }));
  fragment.append(element("rect", { "data-symbol-hit": "true", x: point.x - 11 * unit, y: point.y - 11 * unit, width: 22 * unit, height: 22 * unit, fill: "transparent", "pointer-events": "all" }));
  return fragment;
}

export function renderConnection(connection, target, unit) {
  const fragment = document.createDocumentFragment();
  fragment.append(symbol("circle", "connection", { "data-connection-ring": "true", "data-symbol-hit": "true", cx: target.x, cy: target.y, r: 14 * unit, fill: "none", stroke: "#1f2937", "stroke-width": 2 * unit, "pointer-events": "stroke" }));
  fragment.append(element("rect", { x: target.x - 8 * unit, y: target.y - 8 * unit, width: 16 * unit, height: 16 * unit, fill: "transparent", "pointer-events": "none" }));
  return fragment;
}
