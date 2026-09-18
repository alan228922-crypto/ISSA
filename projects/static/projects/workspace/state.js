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
