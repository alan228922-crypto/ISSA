import { applyEditorAction } from "./editor.js";
import { reduceView } from "./canvas-interaction.js";

function draftFingerprint(draft) {
  const { version, ...content } = draft;
  return JSON.stringify(content);
}

function historyOf(state) {
  return state.history || { past: [], future: [], checkpoint: draftFingerprint(state.draft) };
}

function withCurrentVersion(state, draft) {
  return Object.freeze({ ...draft, version: state.draftVersion });
}

function pruneSelection(state, draft) {
  const collections = { GEOMETRY_NODE: "nodes", PHYSICAL_MEMBER: "physical_members", CONNECTION: "connections", SUPPORT: "supports", NODE_LOAD: "node_loads" };
  const selectedObjects = (state.selectedObjects || []).filter((item) => draft[collections[item.kind]]?.some((record) => record.client_key === item.clientKey));
  return { selectedObjects, selectedObject: selectedObjects.at(-1) || null, focusedObject: null };
}

export function readWorkspaceBootstrap(documentRef = document) {
  const element = documentRef.getElementById("workspace-bootstrap");
  if (!element) throw new Error("WORKSPACE_BOOTSTRAP_MISSING");
  return JSON.parse(element.textContent);
}

export function createWorkspaceState(bootstrap) {
  return Object.freeze({
    draft: bootstrap.draft,
    draftVersion: bootstrap.draft.version,
    history: Object.freeze({ past: [], future: [], checkpoint: draftFingerprint(bootstrap.draft) }),
    readOnly: bootstrap.read_only,
    selectedObject: null,
    selectedObjects: [],
    focusedObject: null,
    viewTransform: Object.freeze({ a: 1, b: 0, c: 0, d: -1, e: 0, f: 0 }),
    cad: Object.freeze({ ortho: false, gridSnap: true, gridVisible: true, objectSnap: true, tracking: true, dynamicInput: true, activeCommand: "SELECT", origin: null, preview: null, snapFeedback: null, trackingGuide: null }),
  });
}

export function applyWorkspaceEditorAction(state, action) {
  const draft = applyEditorAction(state.draft, action);
  if (draft === state.draft || draftFingerprint(draft) === draftFingerprint(state.draft)) return state;
  const history = historyOf(state);
  return Object.freeze({ ...state, draft, history: Object.freeze({ past: [...history.past, state.draft], future: [], checkpoint: history.checkpoint }), dirty: draftFingerprint(draft) !== history.checkpoint });
}

export function undoWorkspaceEdit(state) {
  const history = historyOf(state);
  if (!history.past.length) return state;
  const draft = withCurrentVersion(state, history.past.at(-1));
  return Object.freeze({ ...state, draft, ...pruneSelection(state, draft), history: Object.freeze({ past: history.past.slice(0, -1), future: [state.draft, ...history.future], checkpoint: history.checkpoint }), dirty: draftFingerprint(draft) !== history.checkpoint, resultOverlay: null, analysisResult: null });
}

export function redoWorkspaceEdit(state) {
  const history = historyOf(state);
  if (!history.future.length) return state;
  const draft = withCurrentVersion(state, history.future[0]);
  return Object.freeze({ ...state, draft, ...pruneSelection(state, draft), history: Object.freeze({ past: [...history.past, state.draft], future: history.future.slice(1), checkpoint: history.checkpoint }), dirty: draftFingerprint(draft) !== history.checkpoint, resultOverlay: null, analysisResult: null });
}

export function applyWorkspaceViewEvent(state, event) {
  return Object.freeze({ ...state, viewTransform: reduceView(state.viewTransform, event) });
}

export function applyWorkspaceSaveSuccess(state, response, submittedDraft = state.draft) {
  const draft = Object.freeze({ ...state.draft, version: response.draft_version });
  const history = historyOf(state);
  const checkpoint = draftFingerprint(submittedDraft);
  return Object.freeze({ ...state, draft, draftVersion: response.draft_version, history: Object.freeze({ ...history, checkpoint }), dirty: draftFingerprint(draft) !== checkpoint });
}

export function focusWorkspaceIssue(state, issue) {
  const target = issue?.physical_object;
  const validKinds = ["GEOMETRY_NODE", "PHYSICAL_MEMBER", "CONNECTION", "SUPPORT", "NODE_LOAD"];
  if (!target || !validKinds.includes(target.kind) || typeof target.client_key !== "string" || !target.client_key) return state;
  const object = Object.freeze({ kind: target.kind, clientKey: target.client_key });
  return Object.freeze({ ...state, selectedObject: object, selectedObjects: [object], focusedObject: object });
}

export function predictionCanvasSelection(state) {
  const selected = state?.selectedObject;
  if (state?.draft?.schema_version === "physical-draft-v2") {
    if (selected?.kind === "GEOMETRY_NODE") return Object.freeze({ kind: "NODE", clientKey: selected.clientKey });
    if (selected?.kind === "PHYSICAL_MEMBER") return Object.freeze({ kind: "PHYSICAL_MEMBER", clientKey: selected.clientKey });
    return null;
  }
  if (selected?.kind === "GEOMETRY_NODE") {
    const matches = state.draft.connections.filter((item) => item.geometry_node_client_key === selected.clientKey);
    return matches.length === 1 ? Object.freeze({ kind: "CONNECTION", clientKey: matches[0].client_key }) : null;
  }
  if (!selected || !["CONNECTION", "PHYSICAL_MEMBER"].includes(selected.kind) || typeof selected.clientKey !== "string") return null;
  return Object.freeze({ kind: selected.kind, clientKey: selected.clientKey });
}

export function applyWorkspaceAnalysisSuccess(state, result) {
  return Object.freeze({ ...state, analysisResult: result });
}
