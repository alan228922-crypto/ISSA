import { EditorActionError } from "./editor.js";
import { pickAt, renderedObjectsFromSvg, worldPointFromEvent } from "./canvas-interaction.js";
import { parseCadInput, parseDynamicPoint } from "./cad-input.js";
import { resolvePointerPoint as resolveGeometry } from "./geometry.js";
import { readCoordinateSpace,visibleSvgViewport,svgLocalToClient } from './coordinate-space.js';
import { createInteractionController } from './interaction-controller.js';
import { renderCadPresentation } from "./renderer.js";
import { applyWorkspaceEditorAction, undoWorkspaceEdit, redoWorkspaceEdit } from "./state.js";
import { createStudentLabelResolver } from "./labels.js";
import { candidateMembersAtNode, nodesOnMember, inspectEndpointCandidates } from "./joint-candidates.js";
import { getSnapCandidateIndex,querySnapCandidates } from './snap-candidates.js';

const TOOL_INSTRUCTIONS = Object.freeze({ SELECT: "点击结构查看或修改", NODE: "在画布放置节点；交叉处放置节点即形成桁架铰接", MEMBER: "选择起点，再选择终点", SUPPORT: "选择构件节点放置支座", LOAD: "选择构件节点施加荷载" });
const COMPLETED = Object.freeze({ CREATE_NODE: "已放置节点", PLACE_JOINT_NODE: "已放置节点", CREATE_MEMBER: "已添加构件", CREATE_MEMBER_WITH_ENDPOINT: "已添加构件", CREATE_SUPPORT_AT_NODE: "已放置支座", CREATE_NODE_LOAD_AT_NODE: "已施加荷载" });
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
  const connection = draft.connections?.find((item) => item.client_key === target.clientKey);
  return connection ? { kind: "GEOMETRY_NODE", clientKey: connection.geometry_node_client_key } : null;
}

function updateUi(root, tool, memberStart, contextualInstruction = null) {
  root.dataset.uxTool = tool;
  const supportPalette = root.querySelector("[data-support-palette]");
  const loadPalette = root.querySelector("[data-load-palette]");
  if (supportPalette) supportPalette.hidden = tool !== "SUPPORT";
  if (loadPalette) loadPalette.hidden = tool !== "LOAD";
  for (const button of root.querySelectorAll("[data-workspace-tool]")) {
    const active = button.dataset.workspaceTool === tool;
    button.dataset.active = active ? "true" : "false"; button.setAttribute("aria-pressed", active ? "true" : "false");
  }
  const instruction = root.querySelector("[data-modeling-instruction]");
  if (instruction) instruction.textContent = contextualInstruction || (memberStart ? "请选择构件的终点节点。按 Esc 可取消。" : TOOL_INSTRUCTIONS[tool]);
  for (const input of root.querySelectorAll("[data-cad-distance], [data-cad-angle]")) input.disabled = !(tool === "MEMBER" && memberStart);
}

function cadState(state) { return state.cad || { ortho: false, gridSnap: true, gridVisible: true, activeCommand: "SELECT", origin: null }; }
const effectiveOrtho = (cad) => Boolean(cad.ortho) !== Boolean(cad.temporaryOrtho);
const labelCache=new WeakMap();
const drawingLabels=draft=>{if(!labelCache.has(draft))labelCache.set(draft,createStudentLabelResolver(draft));return labelCache.get(draft);};
function cadStatus(root, cad, resolution = null) {
  const indicator = root.querySelector("#workspace-snap-indicator"); if (!indicator) return;
  indicator.textContent = `ORTHO: ${effectiveOrtho(cad) ? "开" : "关"} · SNAP: ${cad.gridSnap ? "开" : "关"} (Grid) · 对象捕捉: ${cad.objectSnap === false ? "关" : "开"} · 当前: ${resolution?.snapType || "无"}`;
  indicator.dataset.snapType = resolution?.snapType || "";
}

export function bindModelingInteractions({ root, svg, canvasController, showError, readOnly }) {
  if (readOnly) return Object.freeze({ getTool: () => "SELECT" });
  const interaction = createInteractionController({resolvePointer:resolveGeometry,inspectEndpoint:inspectEndpointCandidates});
  const resolvePointerPoint = (args) => {
    const state=canvasController.getState(),coordinates=readCoordinateSpace(svg,args.viewTransform);
    const discovered=args.candidates??(cadState(state).objectSnap===false?[]:querySnapCandidates(getSnapCandidateIndex(state.draft),{clientPoint:args.screenPointer,coordinates}));
    const candidates=discovered.filter(c=>c.nodeClientKey!==args.excludedNodeClientKey||!args.excludedNodeClientKey);
    return interaction.dispatch({type:'POINTER_RESOLVE',...args,candidates,clientPointer:args.screenPointer,coordinates},{draft:state.draft,settings:{ortho:args.ortho,gridSnap:args.gridEnabled}}).state.snapResolution;
  };
  let tool = "SELECT"; let contextualInstruction = null; let pendingNumeric = null; let lastCompletedTool = null;
  const pendingStart=()=>interaction.getState().pendingMemberStart;
  canvasController.setNavigationHandler(event=>interaction.dispatch({type:event==='START'?'PAN_START':'PAN_END'},{draft:canvasController.getState().draft}));
  const refreshUi=()=>{updateUi(root,tool,pendingStart(),contextualInstruction);syncMini();};
  let supportChoice = "PINNED";
  const distanceInput = root.querySelector("[data-cad-distance]"); const angleInput = root.querySelector("[data-cad-angle]");
  const commandInput = root.querySelector("[data-cad-command-input]");
  const dynamicOverlay = root.querySelector("[data-cad-dynamic-overlay]");
  const xInput = dynamicOverlay?.querySelector("[data-cad-x]"); const yInput = dynamicOverlay?.querySelector("[data-cad-y]");
  const miniFields={x:xInput,y:yInput,length:dynamicOverlay?.querySelector('[data-cad-dynamic-length]'),angle:dynamicOverlay?.querySelector('[data-cad-dynamic-angle]'),dx:dynamicOverlay?.querySelector('[data-cad-dynamic-dx]'),dy:dynamicOverlay?.querySelector('[data-cad-dynamic-dy]')};
  const miniMode=()=>pendingStart()?(interaction.getState().dynamicInput?.mode==='RELATIVE'?'RELATIVE':'POLAR'):'XY';
  function syncMini(){
    if(!dynamicOverlay)return;
    const mode=miniMode();
    for(const [name,selector] of [['XY','xy'],['POLAR','polar'],['RELATIVE','relative']])dynamicOverlay.querySelector(`[data-cad-${selector}-fields]`).hidden=name!==mode;
  }
  let acquiredSnap = null;
  const transientCad = (changes, notify = false) => {
    const current = canvasController.getState();
    const next = { ...current, cad: Object.freeze({ ...cadState(current), ...changes }) };
    canvasController.replaceState(next, notify, false);
    renderCadPresentation(svg, next.cad, next);
  };
  const clearInputs = () => {
    if (commandInput) commandInput.value = "";
    if (distanceInput) distanceInput.value = "";
    if (angleInput) angleInput.value = "";
    for(const input of Object.values(miniFields))if(input)input.value='';
  };
  const cancelCommand = () => {
    interaction.dispatch({type:'CANCEL'},{draft:canvasController.getState().draft});
    pendingNumeric = null;
    acquiredSnap = null;
    contextualInstruction = null;
    tool = "SELECT";
    clearInputs();
    transientCad({ activeCommand: "SELECT", origin: null, preview: null, loadPreview: null, gripPreview: null, snapFeedback: null, trackingGuide: null, temporaryOrtho: false });
    if (dynamicOverlay) dynamicOverlay.hidden = true;
    refreshUi();
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
      if (COMPLETED[action.type]) lastCompletedTool = tool;
      contextualInstruction = null;
      root.querySelector("#workspace-save-status").textContent = "未保存修改：有";
      if (COMPLETED[action.type]) root.querySelector("[data-modeling-instruction]").textContent = COMPLETED[action.type];
      return true;
    } catch (error) {
      if (error instanceof EditorActionError) {
        const messages = { EDITOR_UNJOINED_CROSSING_ENDPOINT:"此处是尚未连接的构件交点；请先用「节点」工具建立连接", EDITOR_EXPLICIT_NODE_REQUIRED:"此处已有节点，请通过节点捕捉明确选择节点。", NODE_NOT_ON_MEMBER: "此节点未连接构件；请先绘制构件。", MULTIPLE_JOINTS_AT_NODE: "此节点有多个旧连接，无法确定支座或荷载目标；请先整理模型。", EDITOR_NODE_MOVE_BREAKS_CONNECTION: "移动会使连接脱离构件，原节点未移动。", EDITOR_NODE_MOVE_ZERO_LENGTH: "此位置会使构件长度为零，原节点未移动。" };
        showError({ code: error.code, message: messages[error.code] || "当前工具目标不满足建模条件。" }); return false;
      }
      throw error;
    }
  };
  const memberOrigin = () => pendingStart()?.worldPoint || null;
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
  const existingEndpointAt = (draft, point) => draft.nodes.find((node) => Math.abs(node.x_mm - point.x) < 1e-9 && Math.abs(node.y_mm - point.y) < 1e-9);
  const completeMemberAt = (point, resolution = {kind:'PRECISE',worldPoint:point}) => {
    const profile = memberProfile(); if (!pendingStart() || !profile) return false;
    const current = canvasController.getState();
    if(current.draft.schema_version==='physical-draft-v2'){
      const response=interaction.dispatch({type:'CONFIRM_POINT',resolution},{draft:current.draft,readOnly:false});
      const error=response.effects.find(e=>e.type==='ERROR');if(error){showError(error);return false;}
      const request=response.effects.find(e=>e.type==='REQUEST_MEMBER_COMMIT');if(!request)return false;
      const allocated=[...current.draft.nodes];
      const endpoint=e=>{if(e.kind==='EXISTING_NODE')return {kind:e.kind,nodeClientKey:e.nodeClientKey};const key=nextKey(allocated,'node');allocated.push({client_key:key});return {...e,newNodeClientKey:key};};
      const action={type:'CREATE_MEMBER_BETWEEN_POINTS',start:endpoint(request.start),end:endpoint(request.end),member:{client_key:nextKey(current.draft.physical_members,'member'),material_id:profile.materialId,section_id:profile.sectionId,label:'',is_active:true}};
      const ok=apply(action,{origin:null,preview:null,snapFeedback:null});
      interaction.dispatch({type:'EDITOR_RESULT',ok},{draft:canvasController.getState().draft});
      if(ok){lastCompletedTool=tool;distanceInput.value='';angleInput.value='';refreshUi();}
      return ok;
    }
    const memberStart=pendingStart().nodeClientKey; let endpoint = existingEndpointAt(current.draft, point);
    const newNode = endpoint ? null : { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" };
    endpoint ||= newNode;
    if (endpoint.client_key === memberStart) return false;
    if (!apply({ type: "CREATE_MEMBER_WITH_ENDPOINT", node: newNode, member: { client_key: nextKey(current.draft.physical_members, "member"), start_node_client_key: memberStart, end_node_client_key: endpoint.client_key, material_id: profile.materialId, section_id: profile.sectionId, label: "", is_active: true } }, { origin: point, preview: null, snapFeedback: null })) return false;
    updateDynamics(point); interaction.dispatch({type:'EDITOR_RESULT',ok:true},{draft:canvasController.getState().draft}); distanceInput.value = ""; angleInput.value = ""; refreshUi(); return true;
  };
  const placementEffects = (point, confirmation = "再次确认。", resolution = null) => {
    const draft = canvasController.getState().draft;
    if (draft.schema_version !== "physical-draft-v2") return null;
    if (tool === "NODE") {
      const members = candidateMembersAtNode(draft, { x_mm: point.x, y_mm: point.y });
      return members.length ? `在此建立节点，将连接 ${members.length} 条构件：${members.join("、")}。${confirmation}` : null;
    }
    if (tool !== "MEMBER" || !pendingStart()) return null;
    const memberStart=pendingStart().nodeClientKey;
    const start = {x_mm:memberOrigin().x,y_mm:memberOrigin().y};
    const existingEndpoint = draft.schema_version==='physical-draft-v2'?draft.nodes.find(n=>n.client_key===resolution?.nodeClientKey):existingEndpointAt(draft, point);
    if (existingEndpoint?.client_key === memberStart) return null;
    const passed = nodesOnMember(draft, start, { x_mm: point.x, y_mm: point.y }).filter((key) => key !== memberStart && key !== existingEndpoint?.client_key);
    const endpointMembers = existingEndpoint ? [] : candidateMembersAtNode(draft, { x_mm: point.x, y_mm: point.y });
    const messages = [];
    if (passed.length) messages.push(`构件经过 ${passed.length} 个已有节点：${passed.join("、")}，将在这里形成连接`);
    if (endpointMembers.length) messages.push(`终点将在 ${endpointMembers.length} 条既有构件上建立节点：${endpointMembers.join("、")}`);
    return messages.length ? `${messages.join("；")}。${confirmation}` : null;
  };
  const numericPlacement = (point, commit) => {
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return "INVALID";
    const summary = placementEffects(point);
    const signature = JSON.stringify([tool, pendingStart(), point.x, point.y, summary]);
    if (summary && pendingNumeric !== signature) {
      pendingNumeric = signature;
      contextualInstruction = summary;
      refreshUi();
      return "PENDING";
    }
    pendingNumeric = null;
    contextualInstruction = null;
    return commit() ? "COMMITTED" : "INVALID";
  };
  const chooseTool = (nextTool) => {
    interaction.dispatch({type:'SELECT_TOOL',tool:nextTool},{draft:canvasController.getState().draft});
    tool = nextTool; acquiredSnap = null; contextualInstruction = null; pendingNumeric = null; clearInputs();
    const current = canvasController.getState(); canvasController.replaceState({ ...current, cad: Object.freeze({ ...cadState(current), activeCommand: nextTool, preview: null, loadPreview: null, gripPreview: null, snapFeedback: null, trackingGuide: null, temporaryOrtho: false }) }); refreshUi();
    if (dynamicOverlay) dynamicOverlay.hidden = nextTool === "SELECT" || cadState(current).dynamicInput === false;
  };
  for (const button of root.querySelectorAll("[data-workspace-tool]")) button.addEventListener("click", () => chooseTool(button.dataset.workspaceTool));
  for (const button of root.querySelectorAll("[data-support-choice]")) button.addEventListener("click", () => {
    supportChoice = button.dataset.supportChoice;
    for (const choice of root.querySelectorAll("[data-support-choice]")) choice.setAttribute("aria-pressed", String(choice === button));
  });
  const orthoButton = root.querySelector("[data-cad-ortho]"); const snapButton = root.querySelector("[data-cad-snap]");
  const toggleCad = (field, button) => { const current = canvasController.getState(); const nextCad = Object.freeze({ ...cadState(current), [field]: !cadState(current)[field], trackingGuide: field === "tracking" ? null : cadState(current).trackingGuide }); canvasController.replaceState({ ...current, cad: nextCad }); button.setAttribute("aria-pressed", nextCad[field] ? "true" : "false"); if (field === "dynamicInput" && dynamicOverlay) dynamicOverlay.hidden = !nextCad.dynamicInput || tool === "SELECT"; cadStatus(root, nextCad); };
  orthoButton?.addEventListener("click", () => toggleCad("ortho", orthoButton)); snapButton?.addEventListener("click", () => toggleCad("gridSnap", snapButton));
  for (const [field, selector] of [["gridVisible", "[data-cad-grid-visible]"], ["objectSnap", "[data-cad-object-snap]"], ["tracking", "[data-cad-tracking]"], ["dynamicInput", "[data-cad-dynamic-input]"]]) {
    const button = root.querySelector(selector);
    button?.addEventListener("click", () => toggleCad(field, button));
  }
  const dynamicPoint = () => { const origin = memberOrigin(); const distance = Number(distanceInput?.value); const angle = Number(angleInput?.value); if (!origin || distanceInput?.value === "" || angleInput?.value === "" || !Number.isFinite(distance) || distance <= 0 || !Number.isFinite(angle)) return null; const radians = angle * Math.PI / 180; return { x: origin.x + distance * Math.cos(radians), y: origin.y + distance * Math.sin(radians) }; };
  for (const input of [distanceInput, angleInput]) input?.addEventListener("input", () => updateDynamics(dynamicPoint()));
  for (const [input, field] of [[distanceInput, "DISTANCE"], [angleInput, "ANGLE"]]) input?.addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      if (input === angleInput && !event.shiftKey) { event.preventDefault(); distanceInput.focus(); }
      return;
    }
    if (event.key === "Enter") { event.preventDefault(); const point = dynamicPoint(); if (numericPlacement(point, () => completeMemberAt(point)) === "INVALID") showError({ code: "CAD_INPUT_MALFORMED", message: "请输入大于 0 的距离和有效角度。" }); }
  });
  commandInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return; event.preventDefault();
    if (!['NODE','MEMBER'].includes(tool)) { showError({ code: "CAD_COMMAND_CONTEXT", message: "请先选择节点或构件工具。" }); return; }
    const current = canvasController.getState(); const parsed = parseCadInput(commandInput.value, tool === "MEMBER" ? memberOrigin() : cadState(current).origin);
    if (!parsed.ok) { showError({ code: `CAD_INPUT_${parsed.code}`, message: "坐标格式无效，请输入 x,y、@dx,dy 或 长度<角度。" }); return; }
    const point = resolvePointerPoint({ worldPointer: parsed.point, screenPointer: parsed.point, candidates: [], viewTransform: current.viewTransform, origin: (tool === "MEMBER" ? memberOrigin() : cadState(current).origin) || parsed.point, ortho: false, gridEnabled: false, explicitNumeric: true }).point;
    const result = numericPlacement(point, () => {
      if (tool === "MEMBER") return pendingStart()?completeMemberAt(point):exactPoint(point);
      const placed = apply({ type: "PLACE_JOINT_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } }, { origin: point });
      return placed;
    });
    if (result === "COMMITTED") commandInput.value = "";
    cadStatus(root, cadState(canvasController.getState()));
  });
  const exactPoint = (point) => {
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return false;
    if (tool === "MEMBER" && pendingStart()) return numericPlacement(point, () => completeMemberAt(point)) !== "INVALID";
    if(tool==='MEMBER'){
      const result=interaction.dispatch({type:'PRECISE_POINT',worldPoint:point},{draft:canvasController.getState().draft,readOnly:false});
      const error=result.effects.find(e=>e.type==='ERROR');if(error){showError(error);return false;}
      refreshUi();return Boolean(pendingStart());
    }
    if (tool !== "NODE") return false;
    const current = canvasController.getState();
    return numericPlacement(point, () => {
      const placed = apply({ type: "PLACE_JOINT_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } }, { origin: point });
      return placed;
    }) !== "INVALID";
  };
  for (const input of [xInput, yInput]) input?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const parsed=parseDynamicPoint({mode:'XY',values:{x:xInput.value,y:yInput.value}});
    if(!parsed.ok||!exactPoint(parsed.point))showError({ code: "CAD_INPUT_MALFORMED", message: "请输入有效的 X、Y 坐标。" });
  });
  const miniPair=mode=>({XY:['x','y'],POLAR:['length','angle'],RELATIVE:['dx','dy']}[mode]);
  for(const [field,input] of Object.entries(miniFields)){
    input?.addEventListener('focus',()=>interaction.dispatch({type:'INPUT_FOCUS',field},{draft:canvasController.getState().draft}));
    input?.addEventListener('input',()=>{
      pendingNumeric=null;contextualInstruction=null;
      const mode=miniMode(),values=Object.fromEntries(miniPair(mode).map(k=>[k,miniFields[k].value]));
      interaction.dispatch({type:'INPUT_CHANGE',input:{mode,values,field}},{draft:canvasController.getState().draft});
    });
    input?.addEventListener('keydown',event=>{
      if(event.key==='Tab'){
        event.preventDefault();const order=pendingStart()?['length','angle','dx','dy']:['x','y'];
        const next=order[(order.indexOf(field)+(event.shiftKey?-1:1)+order.length)%order.length];
        interaction.dispatch({type:'INPUT_CHANGE',input:{mode:['dx','dy'].includes(next)?'RELATIVE':pendingStart()?'POLAR':'XY'}},{draft:canvasController.getState().draft});
        syncMini();miniFields[next].focus();
      }
      if(event.key==='Enter'&&['length','angle','dx','dy'].includes(field)){
        event.preventDefault();const mode=miniMode();
        const parsed=parseDynamicPoint({mode,values:Object.fromEntries(miniPair(mode).map(k=>[k,miniFields[k].value])),origin:memberOrigin()});
        if(!pendingStart()||!parsed.ok||!exactPoint(parsed.point))showError({code:'CAD_INPUT_MALFORMED',message:'请输入有效的长度/角度或 ΔX/ΔY。'});
        else if(!pendingStart()){for(const key of ['length','angle','dx','dy'])miniFields[key].value='';svg.focus();}
      }
    });
  }
  for(const input of [commandInput,distanceInput,angleInput])input?.addEventListener('input',()=>{pendingNumeric=null;contextualInstruction=null;});
  root.querySelector("[data-cad-relative-place]")?.addEventListener("click", () => {
    const origin = tool === "MEMBER" ? memberOrigin() : cadState(canvasController.getState()).origin;
    const dxText = root.querySelector("[data-cad-relative-x]")?.value; const dyText = root.querySelector("[data-cad-relative-y]")?.value;
    const dx = Number(dxText); const dy = Number(dyText);
    if (!origin || dxText === "" || dyText === "" || !Number.isFinite(dx) || !Number.isFinite(dy) || !exactPoint({ x: origin.x + dx, y: origin.y + dy })) showError({ code: "CAD_INPUT_MALFORMED", message: "请先确定基准点，并输入有效的 ΔX、ΔY。" });
  });
  const handleCanvasClick = (event, pointerSelection, precisePoint = null) => {
    if (root.dataset.uxStage !== "build") return;
    pendingNumeric = null;
    contextualInstruction = null;
    const current = canvasController.getState(); const target = targetAtClick(event, svg, ["GEOMETRY_NODE", "CONNECTION"]); if (tool === "SELECT") return;
    const screen = precisePoint || { x: event.clientX, y: event.clientY };
    const locationEvent = { clientX: screen.x, clientY: screen.y };
    if (tool === "NODE") {
      if (pointerSelection?.kind === "SUPPORT") return;
      const world = worldPointFromEvent(svg, locationEvent); const cad = cadState(current);
      const resolved = world && resolvePointerPoint({ worldPointer: world, screenPointer: screen, candidates: null, viewTransform: current.viewTransform, origin: cad.origin || world, ortho: effectiveOrtho(cad), gridEnabled: cad.gridSnap, explicitNumeric: false });
      const point = resolved?.point; if (!point) return;
      if (resolved.nodeClientKey) {
        apply({ type: "CONNECT_NODE", nodeClientKey: resolved.nodeClientKey });
        cadStatus(root, cad, resolved); return;
      }
      apply({ type: "PLACE_JOINT_NODE", node: { client_key: nextKey(current.draft.nodes, "node"), x_mm: point.x, y_mm: point.y, label: "" } }, { origin: point, preview: null, snapFeedback: null }); cadStatus(root, cadState(canvasController.getState()), resolved); return;
    }
    if (tool === "MEMBER") {
      const world = worldPointFromEvent(svg, locationEvent); const cad = cadState(current); if (!world) return true;
      const resolved = resolvePointerPoint({worldPointer:world,screenPointer:screen,candidates:null,viewTransform:current.viewTransform,origin:memberOrigin(),ortho:effectiveOrtho(cad),gridEnabled:cad.gridSnap,explicitNumeric:false});
      if (!pendingStart()) { if(current.draft.schema_version!=='physical-draft-v2'&&!resolved.nodeClientKey)return true; const response=interaction.dispatch({type:'CONFIRM_POINT',resolution:resolved},{draft:current.draft,readOnly:false});for(const effect of response.effects)if(effect.type==='ERROR')showError(effect);refreshUi();return true; }
      completeMemberAt(resolved.worldPoint,resolved);cadStatus(root,cadState(canvasController.getState()),resolved);return true;
    }
    const node = nodeTarget(current.draft, target);
    if (!node) {
      contextualInstruction = "请点击构件节点放置支座或荷载；若尚无构件，请先绘制构件。";
      refreshUi();
      return;
    }
    if (tool === "SUPPORT") {
      const clientKey = nextKey(current.draft.supports, "support");
      const support = supportChoice === "PINNED" ? { support_type: "PINNED", restrained_axis: null } : { support_type: "ROLLER", restrained_axis: supportChoice.at(-1) };
      if (apply({ type: "CREATE_SUPPORT_AT_NODE", nodeClientKey: node.clientKey, support: { client_key: clientKey, ...support } })) return { kind: "SUPPORT", clientKey };
    }
    if (tool === "LOAD") {
      const clientKey = nextKey(current.draft.node_loads, "load");
      if (apply({ type: "CREATE_NODE_LOAD_AT_NODE", nodeClientKey: node.clientKey, nodeLoad: { client_key: clientKey, fx_N: 0, fy_N: -100, label: "" } })) return { kind: "NODE_LOAD", clientKey };
    }
  };
  canvasController.setCanvasClickHandler((...args)=>{try{return handleCanvasClick(...args);}catch(error){showError({code:error.code||'CAD_INTERACTION_ERROR',message:error.message});return true;}});
  svg.addEventListener('cad-coordinate-error',event=>{cancelCommand();showError({code:event.detail.code,message:event.detail.message});});
  const gripPosition = (clientKey, world, screen) => {
    if (!world) return null;
    const state = canvasController.getState(); const cad = cadState(state);
    const original = state.draft.nodes.find((node) => node.client_key === clientKey);
    if (!original) return null;
    const origin = { x: original.x_mm, y: original.y_mm };
    const resolved = resolvePointerPoint({ worldPointer: world, screenPointer: screen, candidates:null,excludedNodeClientKey:clientKey, viewTransform: state.viewTransform, origin, ortho: effectiveOrtho(cad), gridEnabled: cad.gridSnap, explicitNumeric: false });
    return { point: resolved.point, original, draft: state.draft };
  };
  const clearGrip = () => transientCad({ gripPreview: null });
  canvasController.setGripHandlers({
    onPreview: (clientKey, world, screen) => {
      const moved = gripPosition(clientKey, world, screen); if (!moved) return;
      const positions = new Map(moved.draft.nodes.map((node) => [node.client_key, { x: node.x_mm, y: node.y_mm }]));
      const members = moved.draft.physical_members.filter((member) => member.start_node_client_key === clientKey || member.end_node_client_key === clientKey).map((member) => ({
        start: member.start_node_client_key === clientKey ? moved.point : positions.get(member.start_node_client_key),
        end: member.end_node_client_key === clientKey ? moved.point : positions.get(member.end_node_client_key),
      }));
      transientCad({ gripPreview: { point: moved.point, members } });
    },
    onCommit: (clientKey, world, screen) => {
      const moved = gripPosition(clientKey, world, screen); clearGrip(); if (!moved) return;
      const { point, original, draft } = moved;
      if (Math.abs(point.x - original.x_mm) < 1e-9 && Math.abs(point.y - original.y_mm) < 1e-9) return;
      const conflict = draft.nodes.some((node) => node.client_key !== clientKey && Math.abs(node.x_mm - point.x) < 1e-9 && Math.abs(node.y_mm - point.y) < 1e-9);
      if (conflict) { showError({ code: "NODE_MOVE_CONFLICT", message: "目标位置已有节点，请换一个位置；原节点未移动。" }); return; }
      apply({ type: "UPDATE_OBJECT", target: { kind: "GEOMETRY_NODE", clientKey }, changes: { x_mm: point.x, y_mm: point.y } });
    },
    onCancel: clearGrip,
  });
  const handlePointerMove=(world, state, screen) => {
    if (!world) return; const display=v=>String(Math.round(v*1e6)/1e6);root.querySelector("#workspace-pointer-x").textContent = `X: ${display(world.x)} mm`; root.querySelector("#workspace-pointer-y").textContent = `Y: ${display(world.y)} mm`;
    const cad = cadState(state); const resolution = resolvePointerPoint({ worldPointer: world, screenPointer: screen, candidates:null, viewTransform: state.viewTransform, origin: memberOrigin() || cad.origin || world, ortho: effectiveOrtho(cad), gridEnabled: cad.gridSnap, explicitNumeric: false });
    const active = tool !== "SELECT";
    const unconnectedIntersection = resolution.kind==='INTERSECTION';
    let trackingGuide = null;
    if (active && cad.tracking !== false && acquiredSnap && !["NODE", "INT"].includes(resolution.snapType)) {
      const tolerance = 8 / Math.max(.05, Math.abs(state.viewTransform.a));
      if (Math.abs(world.y - acquiredSnap.y) <= tolerance) trackingGuide = { start: acquiredSnap, end: { x: resolution.point.x, y: acquiredSnap.y } };
      else if (Math.abs(world.x - acquiredSnap.x) <= tolerance) trackingGuide = { start: acquiredSnap, end: { x: acquiredSnap.x, y: resolution.point.y } };
    }
    if (active && ["NODE", "INT"].includes(resolution.snapType)) acquiredSnap = resolution.point;
    const labels = drawingLabels(state.draft);
    const studentLabel = resolution.kind === "NODE" ? labels.label("GEOMETRY_NODE", resolution.nodeClientKey) : null;
    transientCad({
      preview: interaction.getState().preview,
      loadPreview: tool === "LOAD" && resolution.snapType === "NODE" ? { point: resolution.point, fx_N: 0, fy_N: -100 } : null,
      snapFeedback: active && resolution.snapType ? { ...resolution, studentLabel, unconnectedIntersection } : null,
      trackingGuide,
    });
    if (dynamicOverlay) {
      dynamicOverlay.hidden = !active || cad.dynamicInput === false;
      if (!dynamicOverlay.hidden) {
        const center = svg.closest(".workspace-center").getBoundingClientRect();
        const focused=dynamicOverlay.contains(document.activeElement);
        if(!focused){
          const space=readCoordinateSpace(svg,state.viewTransform),viewport=visibleSvgViewport(svg,space);
          const topLeft=svgLocalToClient({x:viewport.left,y:viewport.top},space),bottomRight=svgLocalToClient({x:viewport.left+viewport.width,y:viewport.top+viewport.height},space);
          dynamicOverlay.style.left=`${Math.max(topLeft.x-center.left,Math.min(bottomRight.x-center.left-dynamicOverlay.offsetWidth-8,screen.x-center.left+20))}px`;
          dynamicOverlay.style.top=`${Math.max(topLeft.y-center.top,Math.min(bottomRight.y-center.top-dynamicOverlay.offsetHeight-8,screen.y-center.top+20))}px`;
        }
        if (document.activeElement !== xInput) xInput.value = String(resolution.point.x);
        if (document.activeElement !== yInput) yInput.value = String(resolution.point.y);
        const origin = memberOrigin();
        syncMini();
        if(origin&&!focused){const dx=resolution.point.x-origin.x,dy=resolution.point.y-origin.y;
          const values={length:String(Math.hypot(dx,dy)),angle:String(Math.atan2(dy,dx)*180/Math.PI),dx:String(dx),dy:String(dy)};
          for(const [key,value] of Object.entries(values))miniFields[key].value=value;
          interaction.dispatch({type:'INPUT_CHANGE',input:{mode:miniMode(),values}},{draft:state.draft});
        }
      }
    }
    cadStatus(root, cadState(canvasController.getState()), resolution);
    refreshUi();
    if (state.draft.schema_version === "physical-draft-v2" && active && !contextualInstruction) {
      const previewInstruction = placementEffects(resolution.point, "点击确认。",resolution);
      if (previewInstruction) root.querySelector("[data-modeling-instruction]").textContent = previewInstruction;
    } else if (unconnectedIntersection && active && !contextualInstruction) root.querySelector("[data-modeling-instruction]").textContent = "这里有构件交叉，但尚未建立连接。";
    if (pendingStart()) updateDynamics(resolution.point);
  };
  canvasController.setPointerMoveHandler((...args)=>{try{handlePointerMove(...args);}catch(error){transientCad({preview:null,snapFeedback:null,trackingGuide:null});showError({code:error.code||'CAD_INTERACTION_ERROR',message:error.message});}});
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && tool !== "SELECT") { event.preventDefault(); event.stopPropagation(); cancelCommand(); } });
  const editableFocus = (target) => Boolean(target?.closest?.("input, textarea, select, [contenteditable], [role='textbox']"));
  const temporaryOrtho=(down)=>{const response=interaction.dispatch({type:'KEY',key:'Shift',down},{focusedInput:down&&editableFocus(document.activeElement)});transientCad({temporaryOrtho:response.state.temporaryOrtho});cadStatus(root,cadState(canvasController.getState()));};
  root.addEventListener('focusin',event=>{if(editableFocus(event.target)&&cadState(canvasController.getState()).temporaryOrtho)temporaryOrtho(false);});
  const repeatLastTool = () => { if (tool === "SELECT" && lastCompletedTool && root.dataset.uxStage === "build") chooseTool(lastCompletedTool); };
  document.addEventListener("keydown", (event) => {
    const fkeys={F7:'grid-visible',F8:'ortho',F9:'snap',F3:'object-snap'};
    if(fkeys[event.key]&&event.target===svg&&!editableFocus(event.target)){event.preventDefault();root.querySelector(`[data-cad-${fkeys[event.key]}]`)?.click();svg.focus();}
    if (event.key === "Shift" && tool !== "SELECT" && !editableFocus(event.target) && !event.repeat) temporaryOrtho(true);
    if (event.key === "Enter" && !event.repeat && (event.target === svg || event.target === document.body) && !event.altKey && !event.ctrlKey && !event.metaKey && tool === "SELECT" && lastCompletedTool) { event.preventDefault(); repeatLastTool(); }
  });
  document.addEventListener("keyup", (event) => { if (event.key === "Shift")temporaryOrtho(false); });
  window.addEventListener('blur',()=>temporaryOrtho(false));
  document.addEventListener("cad-space-tap", repeatLastTool);
  const undoButton = root.querySelector("[data-cad-undo]"); const redoButton = root.querySelector("[data-cad-redo]");
  const syncHistory = (state) => { if (undoButton) undoButton.disabled = !state.history?.past.length; if (redoButton) redoButton.disabled = !state.history?.future.length; };
  canvasController.subscribeStateChange(syncHistory);
  const travelHistory = (direction) => {
    if (pendingStart()) cancelCommand();
    const current = canvasController.getState();
    const next = direction === "UNDO" ? undoWorkspaceEdit(current) : redoWorkspaceEdit(current);
    if (next === current) return;
    acquiredSnap = null;
    canvasController.replaceState({ ...next, cad: Object.freeze({ ...cadState(next), origin: null, preview: null, gripPreview: null, snapFeedback: null, trackingGuide: null }) });
    root.querySelector("#workspace-save-status").textContent = next.dirty ? "未保存修改：有" : "未保存修改：无";
  };
  undoButton?.addEventListener("click", () => travelHistory("UNDO"));
  redoButton?.addEventListener("click", () => travelHistory("REDO"));
  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented || !["z", "y"].includes(event.key.toLowerCase()) || !(event.ctrlKey || event.metaKey) || event.altKey || editableFocus(event.target) || root.dataset.uxStage !== "build") return;
    const direction = event.key.toLowerCase() === "y" || event.shiftKey ? "REDO" : "UNDO";
    event.preventDefault(); travelHistory(direction);
  });
  svg.addEventListener("pointerleave", () => transientCad({ preview: null, loadPreview: null, snapFeedback: null, trackingGuide: null }));
  canvasController.subscribeStateChange(state=>{
    const had=pendingStart();interaction.dispatch({type:'DRAFT_CHANGED'},{draft:state.draft});
    if(had&&!pendingStart()){pendingNumeric=null;contextualInstruction=null;clearInputs();transientCad({origin:null,preview:null,snapFeedback:null});refreshUi();}
  });
  refreshUi(); cadStatus(root, cadState(canvasController.getState())); syncHistory(canvasController.getState()); return Object.freeze({ getTool: () => tool });
}
