export const GRID_ORIGIN = Object.freeze({ x: 0, y: 0 });
export { GRID_SPACING } from "./grid.js";
import { objectsInMarquee } from "./selection-geometry.js";

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

export function worldPointFromEvent(svg, event) {
  const world = svg.querySelector("[data-world-layer]");
  const matrix = world?.getScreenCTM?.();
  if (!matrix) return null;
  const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
  return Number.isFinite(point.x) && Number.isFinite(point.y) ? { x: point.x, y: point.y } : null;
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
  let gesture = null;
  let spaceHeld = false;
  let spaceTapEligible = false;
  let suppressClick = false;
  let pointerSelection = null;
  let marqueeAnchor = null;
  let canvasClickHandler = null;
  const stateChangeHandlers = new Set();
  let pointerMoveHandler = null;
  let fitHandler = null;
  let lastMiddleClick = null;
  const visibleIdentity = (item) => {
    if (item?.kind !== "CONNECTION") return item;
    const connection = state.draft.connections.find((record) => record.client_key === item.clientKey);
    return connection ? { kind: "GEOMETRY_NODE", clientKey: connection.geometry_node_client_key } : item;
  };
  const notifyStateChange = () => { for (const handler of stateChangeHandlers) handler(state); };
  const redraw = () => render(svg, state.draft, state);
  const select = (selection, redrawSelection = true, additive = false) => {
    const prior = additive ? state.selectedObjects || (state.selectedObject ? [state.selectedObject] : []) : [];
    const incoming = (Array.isArray(selection) ? selection : selection ? [selection] : []).map(visibleIdentity);
    const identities = [...prior];
    for (const item of incoming) {
      const index = identities.findIndex((other) => other.kind === item.kind && other.clientKey === item.clientKey);
      if (additive && index >= 0) identities.splice(index, 1);
      else if (index < 0) identities.push(item);
    }
    state = Object.freeze({ ...state, selectedObjects: identities, selectedObject: identities.at(-1) || null });
    if (redrawSelection) redraw();
    notifyStateChange();
  };
  const dispatchViewEvent = (event) => {
    state = Object.freeze({ ...state, viewTransform: reduceView(state.viewTransform, event) });
    redraw();
    notifyStateChange();
  };
  svg.addEventListener("click", (event) => {
    if (suppressClick) { suppressClick = false; event.preventDefault(); event.stopImmediatePropagation(); return; }
    const createdSelection = canvasClickHandler?.(event);
    const direct = createdSelection || pointerSelection || selectionFromElement(event.target?.closest?.("[data-object-kind]"));
    pointerSelection = null;
    const point = { x: event.clientX, y: event.clientY };
    if (state.cad?.activeCommand === "SELECT") {
      if (marqueeAnchor) {
        commitMarquee(marqueeAnchor.point, point, marqueeAnchor.additive || event.shiftKey);
        marqueeAnchor = null;
        removeMarquee();
        return;
      }
      const hit = direct || pickAt(point, renderedObjectsFromSvg(svg));
      if (!hit) { marqueeAnchor = { point, additive: event.shiftKey }; drawMarquee(point, point); return; }
      select(hit, true, event.shiftKey);
      return;
    }
    select(direct || pickAt(point, renderedObjectsFromSvg(svg)), true, event.shiftKey);
  });
  // Mouse focus is part of an active pointer gesture. Replacing SVG children here
  // would detach the pointer target before pointerup/click is dispatched.
  svg.addEventListener("focusin", (event) => { if (!gesture) select(selectionFromElement(event.target), false); });
  svg.addEventListener("keydown", (event) => {
    if (event.key === "Enter") select(selectionFromElement(event.target));
    const delta = { ArrowLeft: { x: -24, y: 0 }, ArrowRight: { x: 24, y: 0 }, ArrowUp: { x: 0, y: -24 }, ArrowDown: { x: 0, y: 24 } }[event.key];
    if (event.target === svg && delta) { event.preventDefault(); dispatchViewEvent({ type: "PAN", deltaScreen: delta }); }
  });
  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    dispatchViewEvent({ type: "ZOOM", factor: event.deltaY < 0 ? 1.1 : 1 / 1.1, anchorScreen: { x: event.clientX, y: event.clientY } });
  }, { passive: false });
  const removeMarquee = () => svg.querySelector("[data-selection-marquee]")?.remove();
  const drawMarquee = (start, end) => {
    removeMarquee();
    const matrix = svg.getScreenCTM()?.inverse();
    if (!matrix) return;
    const a = new DOMPoint(start.x, start.y).matrixTransform(matrix);
    const b = new DOMPoint(end.x, end.y).matrixTransform(matrix);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    for (const [key, value] of Object.entries({ x: Math.min(a.x,b.x), y: Math.min(a.y,b.y), width: Math.abs(b.x-a.x), height: Math.abs(b.y-a.y), fill: "#3273dc22", stroke: "#3273dc", "stroke-dasharray": "5 3", "pointer-events": "none", "data-selection-marquee": "true" })) rect.setAttribute(key, String(value));
    svg.append(rect);
  };
  const commitMarquee = (start, end, additive) => {
    const rect = { left: Math.min(start.x,end.x), right: Math.max(start.x,end.x), top: Math.min(start.y,end.y), bottom: Math.max(start.y,end.y) };
    const mode = end.x < start.x ? "CROSSING" : "WINDOW";
    select(objectsInMarquee(rect, renderedObjectsFromSvg(svg), mode), true, additive);
  };
  document.addEventListener("keydown", (event) => {
    if (event.code === "Space" && !event.repeat && !document.activeElement?.closest?.("input, textarea, select, [contenteditable], [role='textbox']")) { spaceHeld = true; spaceTapEligible = document.activeElement === svg || document.activeElement === document.body; }
    if (event.key === "Escape" && marqueeAnchor) { marqueeAnchor = null; removeMarquee(); }
    else if (event.key === "Escape" && state.cad?.activeCommand === "SELECT" && state.selectedObject) select(null);
  });
  document.addEventListener("keyup", (event) => {
    if (event.code !== "Space") return;
    spaceHeld = false;
    if (spaceTapEligible) document.dispatchEvent(new Event("cad-space-tap"));
    spaceTapEligible = false;
  });
  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 && event.button !== 1) return;
    if (event.button === 1) event.preventDefault();
    if (spaceHeld) spaceTapEligible = false;
    gesture = { start: { x: event.clientX, y: event.clientY }, last: { x: event.clientX, y: event.clientY }, moved: false, pan: event.button === 1 || spaceHeld, select: event.button === 0 && state.cad?.activeCommand === "SELECT", additive: event.shiftKey };
    pointerSelection = selectionFromElement(event.target?.closest?.("[data-object-kind]"));
    svg.setPointerCapture?.(event.pointerId);
  });
  svg.addEventListener("pointermove", (event) => {
    pointerMoveHandler?.(worldPointFromEvent(svg, event), state, { x: event.clientX, y: event.clientY });
    if (!gesture && marqueeAnchor) drawMarquee(marqueeAnchor.point, { x: event.clientX, y: event.clientY });
    if (!gesture) return;
    const point = { x: event.clientX, y: event.clientY };
    if (distance(point, gesture.start) >= 4) gesture.moved = true;
    if (gesture.moved && gesture.pan) dispatchViewEvent({ type: "PAN", deltaScreen: { x: point.x - gesture.last.x, y: point.y - gesture.last.y } });
    if (gesture.moved && gesture.select) drawMarquee(gesture.start, point);
    gesture.last = point;
  });
  svg.addEventListener("pointerup", (event) => {
    if (!gesture) return;
    if (event.button === 1 && !gesture.moved) {
      const point = { x: event.clientX, y: event.clientY };
      const now = Date.now();
      if (lastMiddleClick && now - lastMiddleClick.time < 450 && distance(point, lastMiddleClick.point) < 6) { fitHandler?.(); lastMiddleClick = null; }
      else lastMiddleClick = { time: now, point };
    } else if (event.button === 1) lastMiddleClick = null;
    if (gesture.moved) {
      if (event.button === 0) suppressClick = true;
      if (gesture.select) {
        const start = gesture.start; const end = { x: event.clientX, y: event.clientY };
        commitMarquee(start, end, gesture.additive);
      }
      marqueeAnchor = null;
    }
    gesture = null; removeMarquee();
    if (svg.hasPointerCapture?.(event.pointerId)) svg.releasePointerCapture(event.pointerId);
  });
  svg.addEventListener("pointercancel", () => { gesture = null; removeMarquee(); });
  const replaceState = (nextState, notify = true, redrawState = true) => {
    if (nextState.cad?.activeCommand !== "SELECT") { marqueeAnchor = null; removeMarquee(); }
    state = nextState;
    if (redrawState) redraw();
    if (notify) notifyStateChange();
  };
  return Object.freeze({
    dispatchViewEvent,
    getState: () => state,
    replaceState,
    setCanvasClickHandler: (handler) => { canvasClickHandler = handler; },
    setStateChangeHandler: (handler) => { stateChangeHandlers.clear(); if (handler) stateChangeHandlers.add(handler); },
    subscribeStateChange: (handler) => { stateChangeHandlers.add(handler); return () => stateChangeHandlers.delete(handler); },
    setPointerMoveHandler: (handler) => { pointerMoveHandler = handler; },
    setFitHandler: (handler) => { fitHandler = handler; },
  });
}
