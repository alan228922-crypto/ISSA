export const GRID_ORIGIN = Object.freeze({ x: 0, y: 0 });
export const GRID_SPACING = 100;

const POINT_TOLERANCE = 10;
const SEGMENT_TOLERANCE = 8;
const PICK_PRIORITY = ["SUPPORT", "NODE_LOAD", "CONNECTION", "GEOMETRY_NODE", "PHYSICAL_MEMBER"];
const DOM_KINDS = Object.freeze({
  GeometryNode: "GEOMETRY_NODE",
  PhysicalMember: "PHYSICAL_MEMBER",
  Connection: "CONNECTION",
  Support: "SUPPORT",
  NodeLoad: "NODE_LOAD",
});

function distance(left, right) {
  return Math.hypot(left.x - right.x, left.y - right.y);
}

function distanceToSegment(point, start, end) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return distance(point, start);
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared));
  return distance(point, { x: start.x + t * dx, y: start.y + t * dy });
}

function hitDistance(screenPoint, hit) {
  if (hit?.type === "POINT" && hit.point) return distance(screenPoint, hit.point);
  if (hit?.type === "SEGMENT" && hit.start && hit.end) return distanceToSegment(screenPoint, hit.start, hit.end);
  return null;
}

export function pickAt(screenPoint, renderedObjects) {
  if (!screenPoint || !Array.isArray(renderedObjects)) return null;
  const candidates = renderedObjects.flatMap((object) => {
    const priority = PICK_PRIORITY.indexOf(object?.kind);
    const hit = hitDistance(screenPoint, object?.hit);
    const tolerance = object?.hit?.type === "POINT" ? POINT_TOLERANCE : SEGMENT_TOLERANCE;
    return priority < 0 || hit === null || hit > tolerance || !object.clientKey ? [] : [{ object, priority, hit }];
  });
  candidates.sort((left, right) => left.priority - right.priority || left.hit - right.hit || `${left.object.kind}:${left.object.clientKey}`.localeCompare(`${right.object.kind}:${right.object.clientKey}`));
  const winner = candidates[0]?.object;
  return winner ? { kind: winner.kind, clientKey: winner.clientKey } : null;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function precise(value) {
  return Number(value.toFixed(12));
}

export function reduceView(view, event) {
  if (event.type === "PAN") return { ...view, e: view.e + event.deltaScreen.x, f: view.f + event.deltaScreen.y };
  if (event.type === "ZOOM") {
    if (!Number.isFinite(event.factor) || event.factor <= 0) throw new Error("ZOOM_FACTOR_INVALID");
    const scale = clamp(Math.abs(view.a) * event.factor, 0.05, 20);
    const ratio = scale / Math.abs(view.a);
    const anchor = event.anchorScreen;
    return { a: precise(view.a * ratio), b: precise(view.b * ratio), c: precise(view.c * ratio), d: precise(view.d * ratio), e: precise(anchor.x - ratio * (anchor.x - view.e)), f: precise(anchor.y - ratio * (anchor.y - view.f)) };
  }
  if (event.type === "FIT_VIEW") {
    if (event.worldBounds === null) return { ...view };
    const { minX, minY, maxX, maxY } = event.worldBounds;
    const width = Math.max(100, maxX - minX);
    const height = Math.max(100, maxY - minY);
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const scale = clamp(Math.min((event.viewport.width - 80) / width, (event.viewport.height - 80) / height), 0.05, 20);
    const a = view.a < 0 ? -scale : scale;
    const d = view.d < 0 ? -scale : scale;
    return { a: precise(a), b: 0, c: 0, d: precise(d), e: precise(event.viewport.width / 2 - a * centerX), f: precise(event.viewport.height / 2 - d * centerY) };
  }
  throw new Error("VIEW_EVENT_INVALID");
}

export function selectionFromElement(element) {
  const kind = DOM_KINDS[element?.getAttribute?.("data-object-kind")];
  const clientKey = element?.getAttribute?.("data-client-key");
  return kind && clientKey ? { kind, clientKey } : null;
}

function screenPoint(matrix, x, y) {
  const point = new DOMPoint(x, y).matrixTransform(matrix);
  return { x: point.x, y: point.y };
}

export function renderedObjectsFromSvg(svg) {
  return [...svg.querySelectorAll("[data-object-kind]")].flatMap((group) => {
    const selection = selectionFromElement(group);
    if (!selection) return [];
    const line = group.querySelector("line");
    if (selection.kind === "PHYSICAL_MEMBER" && line?.getScreenCTM()) {
      const matrix = line.getScreenCTM();
      return [{ ...selection, hit: { type: "SEGMENT", start: screenPoint(matrix, Number(line.getAttribute("x1")), Number(line.getAttribute("y1"))), end: screenPoint(matrix, Number(line.getAttribute("x2")), Number(line.getAttribute("y2"))) } }];
    }
    const bounds = group.getBoundingClientRect();
    return [{ ...selection, hit: { type: "POINT", point: { x: bounds.left + bounds.width / 2, y: bounds.top + bounds.height / 2 } } }];
  });
}

export function bindCanvasInteractions(svg, initialState, render) {
  let state = initialState;
  let panStart = null;
  const redraw = () => render(svg, state.draft, state);
  const select = (selection) => {
    if (!selection) return;
    state = Object.freeze({ ...state, selectedObject: selection });
    redraw();
  };
  const dispatchViewEvent = (event) => {
    state = Object.freeze({ ...state, viewTransform: reduceView(state.viewTransform, event) });
    redraw();
  };
  svg.addEventListener("click", (event) => select(pickAt({ x: event.clientX, y: event.clientY }, renderedObjectsFromSvg(svg))));
  svg.addEventListener("focusin", (event) => select(selectionFromElement(event.target)));
  svg.addEventListener("keydown", (event) => {
    if (event.key === "Enter") select(selectionFromElement(event.target));
  });
  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    dispatchViewEvent({ type: "ZOOM", factor: event.deltaY < 0 ? 1.1 : 1 / 1.1, anchorScreen: { x: event.clientX, y: event.clientY } });
  }, { passive: false });
  svg.addEventListener("pointerdown", (event) => { panStart = { x: event.clientX, y: event.clientY }; });
  svg.addEventListener("pointermove", (event) => {
    if (!panStart) return;
    dispatchViewEvent({ type: "PAN", deltaScreen: { x: event.clientX - panStart.x, y: event.clientY - panStart.y } });
    panStart = { x: event.clientX, y: event.clientY };
  });
  svg.addEventListener("pointerup", () => { panStart = null; });
  return Object.freeze({ dispatchViewEvent, getState: () => state });
}
