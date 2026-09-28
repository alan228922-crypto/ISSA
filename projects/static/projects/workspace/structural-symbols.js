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
  return defs;
}

export function renderMember(member, start, end, unit, visualState = {}) {
  return symbol("line", "member", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, stroke: visualState.result?.color || "currentColor", "stroke-width": 8, "stroke-dasharray": visualState.result?.dash || "none" });
}

export function renderSupport(support, target, unit) {
  const fragment = document.createDocumentFragment();
  fragment.append(symbol("path", "support", { d: `M ${target.x - 14 * unit} ${target.y - 32 * unit} L ${target.x + 14 * unit} ${target.y - 32 * unit} L ${target.x} ${target.y - 10 * unit} Z`, fill: "white", stroke: "currentColor", "stroke-width": 2.5 * unit }));
  if (support.support_type === "ROLLER") fragment.append(element("line", support.restrained_axis === "X" ? { x1: target.x - 12 * unit, y1: target.y - 38 * unit, x2: target.x + 12 * unit, y2: target.y - 38 * unit, stroke: "currentColor", "stroke-width": 2.5 * unit } : { x1: target.x, y1: target.y - 34 * unit, x2: target.x, y2: target.y - 46 * unit, stroke: "currentColor", "stroke-width": 2.5 * unit }));
  return fragment;
}

export function renderLoad(load, target, unit) {
  const dx = load.fx_N === 0 ? 0 : (load.fx_N > 0 ? 36 * unit : -36 * unit);
  const dy = load.fy_N === 0 ? 0 : (load.fy_N > 0 ? 36 * unit : -36 * unit);
  const length = Math.hypot(dx, dy);
  if (!length) return symbol("circle", "load", { cx: target.x, cy: target.y, r: 20 * unit, fill: "none", stroke: "currentColor", "stroke-width": 2.5 * unit });
  return symbol("line", "load", { x1: target.x - dx, y1: target.y - dy, x2: target.x - dx / length * 8 * unit, y2: target.y - dy / length * 8 * unit, stroke: "currentColor", "stroke-width": 2.5 * unit, "marker-end": "url(#workspace-load-arrow)" });
}

export function renderNode(node, point) {
  return symbol("circle", "node", { cx: point.x, cy: point.y, r: 7, fill: "currentColor" });
}

export function renderConnection(connection, target, unit) {
  return symbol("rect", "connection", { x: target.x - 8 * unit, y: target.y - 8 * unit, width: 16 * unit, height: 16 * unit, fill: "white", stroke: "currentColor", "stroke-width": 2.5 * unit });
}
