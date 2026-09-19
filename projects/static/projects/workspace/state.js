import { applyEditorAction } from "./editor.js";
import { reduceView } from "./canvas-interaction.js";

export function readWorkspaceBootstrap(documentRef = document) {
  const element = documentRef.getElementById("workspace-bootstrap");
  if (!element) throw new Error("WORKSPACE_BOOTSTRAP_MISSING");
  return JSON.parse(element.textContent);
}

export function createWorkspaceState(bootstrap) {
  return Object.freeze({
    draft: bootstrap.draft,
    draftVersion: bootstrap.draft.version,
    readOnly: bootstrap.read_only,
    selectedObject: null,
    focusedObject: null,
    viewTransform: Object.freeze({ a: 1, b: 0, c: 0, d: -1, e: 0, f: 0 }),
  });
}

export function applyWorkspaceEditorAction(state, action) {
  return Object.freeze({...state, draft: applyEditorAction(state.draft, action), dirty: true});
}

export function applyWorkspaceViewEvent(state, event) {
  return Object.freeze({ ...state, viewTransform: reduceView(state.viewTransform, event) });
}

export function applyWorkspaceSaveSuccess(state, response, submittedDraft = state.draft) {
  const draft = Object.freeze({ ...state.draft, version: response.draft_version });
  return Object.freeze({ ...state, draft, draftVersion: response.draft_version, dirty: state.draft !== submittedDraft });
}

export function focusWorkspaceIssue(state, issue) {
  const target = issue?.physical_object;
  const validKinds = ["GEOMETRY_NODE", "PHYSICAL_MEMBER", "CONNECTION", "SUPPORT", "NODE_LOAD"];
  if (!target || !validKinds.includes(target.kind) || typeof target.client_key !== "string" || !target.client_key) return state;
  const object = Object.freeze({ kind: target.kind, clientKey: target.client_key });
  return Object.freeze({ ...state, selectedObject: object, focusedObject: object });
}

export function predictionCanvasSelection(state) {
  const selected = state?.selectedObject;
  if (!selected || !["CONNECTION", "PHYSICAL_MEMBER"].includes(selected.kind) || typeof selected.clientKey !== "string") return null;
  return Object.freeze({ kind: selected.kind, clientKey: selected.clientKey });
}

export function applyWorkspaceAnalysisSuccess(state, result) {
  return Object.freeze({ ...state, analysisResult: result });
}
