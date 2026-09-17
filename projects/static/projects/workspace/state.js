import { applyEditorAction } from "./editor.js";

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
  });
}

export function applyWorkspaceEditorAction(state, action) {
  return Object.freeze({...state, draft: applyEditorAction(state.draft, action), dirty: true});
}
