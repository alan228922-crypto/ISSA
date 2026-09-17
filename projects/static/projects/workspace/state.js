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
