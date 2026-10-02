export const GRID_ORIGIN = Object.freeze({ x: 0, y: 0 });
export { GRID_SPACING } from "./grid.js";
import { objectsInMarquee } from "./selection-geometry.js";
import { createStudentLabelResolver } from "./labels.js";
import { candidateMembersAtNode } from "./joint-candidates.js";
import { readCoordinateSpace, clientToWorld, worldToClient, clientPointToSvgLocal, clientDeltaToSvgLocal } from './coordinate-space.js';
import { renderWorkspaceView } from './renderer.js';

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

export function pickCandidatesAt(screenPoint, renderedObjects) {
  if (!screenPoint || !Array.isArray(renderedObjects)) return null;
  const candidates = renderedObjects.flatMap((object) => {
    const priority = PICK_PRIORITY.indexOf(object?.kind);
    const hit = hitDistance(screenPoint, object?.hit);
    const tolerance = object?.hit?.type === "POINT" ? POINT_TOLERANCE : SEGMENT_TOLERANCE;
    return priority < 0 || hit === null || hit > tolerance || !object.clientKey ? [] : [{ object, priority, hit }];
  });
  candidates.sort((left, right) => left.priority - right.priority || left.hit - right.hit || `${left.object.kind}:${left.object.clientKey}`.localeCompare(`${right.object.kind}:${right.object.clientKey}`));
  return candidates.map(({ object }) => ({ kind: object.kind, clientKey: object.clientKey }));
}

export function pickAt(screenPoint, renderedObjects) {
  return pickCandidatesAt(screenPoint, renderedObjects)?.[0] || null;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function precise(value) {
  return Number(value.toFixed(12));
}

export function reduceView(view, event) {
  if (event.type === "PAN") { const delta=event.deltaSvgLocal || event.deltaScreen; return { ...view, e: view.e + delta.x, f: view.f + delta.y }; }
  if (event.type === "ZOOM") {
    if (!Number.isFinite(event.factor) || event.factor <= 0) throw new Error("ZOOM_FACTOR_INVALID");
    const scale = clamp(Math.abs(view.a) * event.factor, 0.05, 20);
    const ratio = scale / Math.abs(view.a);
    const anchor = event.anchorSvgLocal || event.anchorScreen;
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
    return { a: precise(a), b: 0, c: 0, d: precise(d), e: precise((event.viewport.left || 0) + event.viewport.width / 2 - a * centerX), f: precise((event.viewport.top || 0) + event.viewport.height / 2 - d * centerY) };
  }
  throw new Error("VIEW_EVENT_INVALID");
}

export function selectionFromElement(element) {
  const kind = DOM_KINDS[element?.getAttribute?.("data-object-kind")];
  const clientKey = element?.getAttribute?.("data-client-key");
  return kind && clientKey ? { kind, clientKey } : null;
}

export function worldPointFromEvent(svg, event) {
  try { return clientToWorld({x:event.clientX,y:event.clientY},readCoordinateSpace(svg)); }
  catch(error){svg.dispatchEvent(new CustomEvent('cad-coordinate-error',{detail:error}));return null;}
}

export function renderedObjectsFromSvg(svg) {
  return [...svg.querySelectorAll("[data-object-kind]")].flatMap((group) => {
    const selection = selectionFromElement(group);
    if (!selection) return [];
    const line = group.querySelector("line");
    if (selection.kind === "PHYSICAL_MEMBER" && line) {
      const space = readCoordinateSpace(svg);
      return [{ ...selection, hit: { type: "SEGMENT", start: worldToClient({x:Number(line.getAttribute('x1')),y:Number(line.getAttribute('y1'))},space), end: worldToClient({x:Number(line.getAttribute('x2')),y:Number(line.getAttribute('y2'))},space) } }];
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
  let lastPointerUp = null;
  const stateChangeHandlers = new Set();
  let pointerMoveHandler = null;
  let fitHandler = null;
  let gripHandlers = null;
  let propertiesHandler = null;
  let hoveredElement = null;
  let overlapChooser = null;
  let lastMiddleClick = null;
  let lastClientPointer=null;
  let navigationHandler=null;
  const resolvePresentation=()=>{if(lastClientPointer)pointerMoveHandler?.(worldPointFromEvent(svg,{clientX:lastClientPointer.x,clientY:lastClientPointer.y}),state,lastClientPointer);};
  const visibleIdentity = (item) => {
    if (item?.kind !== "CONNECTION") return item;
    const connection = state.draft.connections?.find((record) => record.client_key === item.clientKey);
    return connection ? { kind: "GEOMETRY_NODE", clientKey: connection.geometry_node_client_key } : item;
  };
  const notifyStateChange = () => { for (const handler of stateChangeHandlers) handler(state); };
  const redraw = () => { hoveredElement = null; render(svg, state.draft, state); };
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
    renderWorkspaceView(svg,state.draft,state,readCoordinateSpace(svg,state.viewTransform));
    notifyStateChange();
    resolvePresentation();
  };
  const closeChooser = () => { overlapChooser?.remove(); overlapChooser = null; };
  const showChooser = (candidates, point, additive) => {
    closeChooser();
    const parent = svg.parentElement;
    const bounds = parent.getBoundingClientRect();
    const labels = createStudentLabelResolver(state.draft);
    const panel = document.createElement("div");
    panel.dataset.cadOverlapChooser = "true";
    panel.setAttribute("role", "group"); panel.setAttribute("aria-label", "选择重叠对象");
    panel.style.left = `${Math.max(0, Math.min(bounds.width - 150, point.x - bounds.left + 12))}px`;
    panel.style.top = `${Math.max(0, Math.min(bounds.height - 130, point.y - bounds.top + 12))}px`;
    const v2 = state.draft.schema_version === "physical-draft-v2";
    const nodeChoices = candidates.filter((item) => item.kind === "GEOMETRY_NODE");
    if (v2 && nodeChoices.length > 1) {
      const warning = document.createElement("p"); warning.textContent = "这里有多个位置相同但彼此不连接的旧模型节点。请选择具体节点。"; panel.append(warning);
    }
    for (const candidate of candidates) {
      const button = document.createElement("button"); button.type = "button";
      button.textContent = labels.label(candidate.kind, candidate.clientKey);
      if (v2 && candidate.kind === "GEOMETRY_NODE") {
        const target = state.draft.nodes.find((row) => row.client_key === candidate.clientKey);
        const passing = target ? candidateMembersAtNode(state.draft, target) : [];
        const joined = passing.filter((memberKey) => {
          const member = state.draft.physical_members.find((row) => row.client_key === memberKey);
          return [member.start_node_client_key, member.end_node_client_key].includes(candidate.clientKey)
            || state.draft.member_joint_incidences.some((row) => row.member_client_key === memberKey && row.node_client_key === candidate.clientKey);
        });
        const unjoined = passing.filter((memberKey) => !joined.includes(memberKey));
        const supportCount = state.draft.supports.filter((row) => row.target_node_client_key === candidate.clientKey).length;
        const loadCount = state.draft.node_loads.filter((row) => row.target_node_client_key === candidate.clientKey).length;
        button.textContent += ` · 连接构件 ${joined.join("、") || "无"} · 未连接 ${unjoined.join("、") || "无"} · 支座 ${supportCount} · 荷载 ${loadCount}`;
      }
      button.addEventListener("click", () => { closeChooser(); select(candidate, true, additive); });
      panel.append(button);
    }
    parent.append(panel); overlapChooser = panel;
  };
  svg.addEventListener("click", (event) => {
    if (suppressClick) { suppressClick = false; lastPointerUp = null; event.preventDefault(); event.stopImmediatePropagation(); return; }
    closeChooser();
    const precisePoint = lastPointerUp && Math.abs(lastPointerUp.x - event.clientX) <= 1 && Math.abs(lastPointerUp.y - event.clientY) <= 1 ? lastPointerUp : null;
    lastPointerUp = null;
    const createdSelection = canvasClickHandler?.(event, pointerSelection, precisePoint);
    if (createdSelection === true) { pointerSelection=null; return; }
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
      const rendered = renderedObjectsFromSvg(svg);
      const candidates = pickCandidatesAt(point, rendered);
      const pointCandidates = candidates.filter((candidate) => rendered.some((item) => item.kind === candidate.kind && item.clientKey === candidate.clientKey && item.hit.type === "POINT"));
      if (candidates.length > 1 && (!direct || pointCandidates.length > 1)) { showChooser(candidates, point, event.shiftKey); return; }
      const hit = direct || candidates[0];
      if (!hit) { marqueeAnchor = { point, additive: event.shiftKey }; drawMarquee(point, point); return; }
      select(hit, true, event.shiftKey);
      return;
    }
    select(direct || pickAt(point, renderedObjectsFromSvg(svg)), true, event.shiftKey);
  });
  svg.addEventListener("dblclick", (event) => {
    if (state.cad?.activeCommand !== "SELECT") return;
    const direct = selectionFromElement(event.target?.closest?.("[data-object-kind]"));
    const hit = direct || pickAt({ x: event.clientX, y: event.clientY }, renderedObjectsFromSvg(svg));
    if (!hit) return;
    select(hit);
    propertiesHandler?.();
  });
  // Mouse focus is part of an active pointer gesture. Replacing SVG children here
  // would detach the pointer target before pointerup/click is dispatched.
  svg.addEventListener("focusin", (event) => { if (!gesture && event.target !== svg) select(selectionFromElement(event.target), false); });
  svg.addEventListener("keydown", (event) => {
    if (event.key === "Enter") select(selectionFromElement(event.target));
    const delta = { ArrowLeft: { x: -24, y: 0 }, ArrowRight: { x: 24, y: 0 }, ArrowUp: { x: 0, y: -24 }, ArrowDown: { x: 0, y: 24 } }[event.key];
    if (event.target === svg && delta) { event.preventDefault(); dispatchViewEvent({ type: "PAN", deltaSvgLocal: clientDeltaToSvgLocal({x:0,y:0},delta,readCoordinateSpace(svg,state.viewTransform)) }); }
  });
  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    lastClientPointer={x:event.clientX,y:event.clientY};
    try { dispatchViewEvent({ type: "ZOOM", factor: event.deltaY < 0 ? 1.1 : 1 / 1.1, anchorSvgLocal: clientPointToSvgLocal({ x: event.clientX, y: event.clientY },readCoordinateSpace(svg,state.viewTransform)) }); }
    catch(error){svg.dispatchEvent(new CustomEvent('cad-coordinate-error',{detail:error}));}
  }, { passive: false });
  const removeMarquee = () => svg.querySelector("[data-selection-marquee]")?.remove();
  const drawMarquee = (start, end) => {
    removeMarquee();
    const space = readCoordinateSpace(svg,state.viewTransform);
    const a = clientPointToSvgLocal(start,space);
    const b = clientPointToSvgLocal(end,space);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const crossing = end.x < start.x;
    for (const [key, value] of Object.entries({ x: Math.min(a.x,b.x), y: Math.min(a.y,b.y), width: Math.abs(b.x-a.x), height: Math.abs(b.y-a.y), fill: crossing ? "#0f766e33" : "#3273dc22", stroke: crossing ? "#0f766e" : "#3273dc", "stroke-dasharray": crossing ? "8 3" : "none", "pointer-events": "none", "data-selection-marquee": "true", "data-selection-mode": crossing ? "CROSSING" : "WINDOW" })) rect.setAttribute(key, String(value));
    svg.append(rect);
  };
  const commitMarquee = (start, end, additive) => {
    const rect = { left: Math.min(start.x,end.x), right: Math.max(start.x,end.x), top: Math.min(start.y,end.y), bottom: Math.max(start.y,end.y) };
    const mode = end.x < start.x ? "CROSSING" : "WINDOW";
    select(objectsInMarquee(rect, renderedObjectsFromSvg(svg), mode), true, additive);
  };
  document.addEventListener("keydown", (event) => {
    if (event.code === "Space" && !event.repeat && !document.activeElement?.closest?.("input, textarea, select, [contenteditable], [role='textbox']")) { spaceHeld = true; spaceTapEligible = document.activeElement === svg || document.activeElement === document.body; }
    if (event.key === "Escape" && overlapChooser) closeChooser();
    else if (event.key === "Escape" && marqueeAnchor) { marqueeAnchor = null; removeMarquee(); }
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
    const grip = event.button === 0 && !spaceHeld && state.cad?.activeCommand === "SELECT" ? event.target?.closest?.("[data-cad-node-grip]") : null;
    gesture = { pointerId:event.pointerId,start: { x: event.clientX, y: event.clientY }, last: { x: event.clientX, y: event.clientY }, moved: false, pan: event.button === 1 || spaceHeld, select: event.button === 0 && !grip && state.cad?.activeCommand === "SELECT", gripTarget: grip?.getAttribute("data-cad-node-grip") || null, additive: event.shiftKey };
    pointerSelection = grip ? { kind: "GEOMETRY_NODE", clientKey: grip.getAttribute("data-cad-node-grip") } : selectionFromElement(event.target?.closest?.("[data-object-kind]"));
    if(gesture.pan)navigationHandler?.('START');
    svg.setPointerCapture?.(event.pointerId);
  });
  svg.addEventListener("pointermove", (event) => {
    lastClientPointer={x:event.clientX,y:event.clientY};
    if (gesture?.gripTarget) {
      const point = { x: event.clientX, y: event.clientY };
      if (distance(point, gesture.start) >= 4) gesture.moved = true;
      if (gesture.moved) gripHandlers?.onPreview?.(gesture.gripTarget, worldPointFromEvent(svg, event), point);
      gesture.last = point;
      return;
    }
    if(gesture?.pan){
      const point=lastClientPointer;
      if(distance(point,gesture.start)>=4)gesture.moved=true;
      if(gesture.moved)try{dispatchViewEvent({type:'PAN',deltaSvgLocal:clientDeltaToSvgLocal(gesture.last,point,readCoordinateSpace(svg,state.viewTransform))});}catch(error){cancelGesture();svg.dispatchEvent(new CustomEvent('cad-coordinate-error',{detail:error}));return;}
      gesture.last=point;return;
    }
    resolvePresentation();
    if (!gesture && marqueeAnchor) drawMarquee(marqueeAnchor.point, { x: event.clientX, y: event.clientY });
    if (!gesture && state.cad?.activeCommand === "SELECT") {
      const direct = event.target?.closest?.("[data-object-kind]");
      const nearest = direct ? selectionFromElement(direct) : pickAt({ x: event.clientX, y: event.clientY }, renderedObjectsFromSvg(svg));
      const next = direct || (nearest && [...svg.querySelectorAll("[data-object-kind]")].find((item) => selectionFromElement(item)?.kind === nearest.kind && item.getAttribute("data-client-key") === nearest.clientKey));
      if (hoveredElement !== next) { hoveredElement?.removeAttribute("data-hovered"); hoveredElement = next || null; hoveredElement?.setAttribute("data-hovered", "true"); }
    }
    if (!gesture) return;
    const point = { x: event.clientX, y: event.clientY };
    if (distance(point, gesture.start) >= 4) gesture.moved = true;
    if (gesture.moved && gesture.select) drawMarquee(gesture.start, point);
    gesture.last = point;
  });
  svg.addEventListener("pointerup", (event) => {
    if (!gesture) return;
    lastPointerUp = { x: event.clientX, y: event.clientY };
    if (gesture.gripTarget && gesture.moved) {
      suppressClick = true;
      gripHandlers?.onCommit?.(gesture.gripTarget, worldPointFromEvent(svg, event), { x: event.clientX, y: event.clientY });
    }
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
    if(gesture.pan)navigationHandler?.('END');
    gesture = null; removeMarquee();
    if (svg.hasPointerCapture?.(event.pointerId)) svg.releasePointerCapture(event.pointerId);
  });
  const cancelGesture=()=>{
    if(gesture?.gripTarget)gripHandlers?.onCancel?.();
    if(gesture?.pan)navigationHandler?.('END');
    const pointerId=gesture?.pointerId;gesture=null;lastPointerUp=null;spaceHeld=false;spaceTapEligible=false;marqueeAnchor=null;suppressClick=false;removeMarquee();
    if(pointerId!=null&&svg.hasPointerCapture?.(pointerId))svg.releasePointerCapture(pointerId);
    svg.dispatchEvent(new CustomEvent('cad-gesture-cancel'));
  };
  svg.addEventListener('pointercancel',cancelGesture);
  svg.addEventListener('lostpointercapture',()=>{if(gesture)cancelGesture();});
  window.addEventListener('blur',cancelGesture);
  svg.addEventListener("pointerleave", () => { hoveredElement?.removeAttribute("data-hovered"); hoveredElement = null; });
  const replaceState = (nextState, notify = true, redrawState = true) => {
    if (nextState.cad?.activeCommand !== "SELECT") { marqueeAnchor = null; removeMarquee(); closeChooser(); }
    state = nextState;
    if (redrawState) redraw();
    if (notify) notifyStateChange();
  };
  return Object.freeze({
    refreshPointerPresentation:resolvePresentation,
    dispatchViewEvent,
    getState: () => state,
    replaceState,
    setCanvasClickHandler: (handler) => { canvasClickHandler = handler; },
    setStateChangeHandler: (handler) => { stateChangeHandlers.clear(); if (handler) stateChangeHandlers.add(handler); },
    subscribeStateChange: (handler) => { stateChangeHandlers.add(handler); return () => stateChangeHandlers.delete(handler); },
    setPointerMoveHandler: (handler) => { pointerMoveHandler = handler; },
    setNavigationHandler:(handler)=>{navigationHandler=handler;},
    setFitHandler: (handler) => { fitHandler = handler; },
    setGripHandlers: (handlers) => { gripHandlers = handlers; },
    setPropertiesHandler: (handler) => { propertiesHandler = handler; },
  });
}
