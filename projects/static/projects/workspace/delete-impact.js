import { applyEditorAction, EditorActionError } from "./editor.js";
import { memberParticipationByNode } from "./draft-topology.js";

const identity = target => `${target.kind}:${target.clientKey}`;
const unique = targets => [...new Map(targets.map(target => [identity(target), { kind: target.kind, clientKey: target.clientKey }])).values()];
const counts = targets => targets.reduce((result, target) => ({ ...result, [target.kind]: (result[target.kind] || 0) + 1 }), {});

// Extracted from the existing deleteSelection preview: compare newly lost fields,
// not whether the whole object was already incomplete for some unrelated reason.
function directImpact(before, after) {
  const result = [];
  const priorMembers = new Map(before.physical_members.map(row => [row.client_key, row]));
  for (const row of after.physical_members) {
    const prior = priorMembers.get(row.client_key);
    if (prior && ((prior.start_node_client_key && !row.start_node_client_key) || (prior.end_node_client_key && !row.end_node_client_key))) {
      result.push({ kind: "PHYSICAL_MEMBER", clientKey: row.client_key });
    }
  }
  const beforeNodes = new Set(before.nodes.map(row => row.client_key));
  const afterNodes = new Set(after.nodes.map(row => row.client_key));
  for (const [kind, collection] of [["SUPPORT", "supports"], ["NODE_LOAD", "node_loads"]]) {
    const prior = new Map(before[collection].map(row => [row.client_key, row]));
    for (const row of after[collection]) {
      if (beforeNodes.has(prior.get(row.client_key)?.target_node_client_key) && !afterNodes.has(row.target_node_client_key)) {
        result.push({ kind, clientKey: row.client_key });
      }
    }
  }
  return result;
}

export function previewDeleteImpact(originalDraft, selectedTargets) {
  if (originalDraft.schema_version !== "physical-draft-v2") throw new EditorActionError("UNSUPPORTED_DRAFT_SCHEMA");
  const selected = unique(selectedTargets);
  const candidate = targets => targets.length ? applyEditorAction(originalDraft, { type: "DELETE_OBJECTS", targets }) : originalDraft;
  const directAffected = directImpact(originalDraft, candidate(selected));
  const firstLevel = unique([...selected, ...directAffected]);
  const afterFirstLevel = candidate(firstLevel);
  const deletedMembers = new Set(firstLevel.filter(row => row.kind === "PHYSICAL_MEMBER").map(row => row.clientKey));
  const beforeParticipation = memberParticipationByNode(originalDraft);
  const afterParticipation = memberParticipationByNode(afterFirstLevel);
  const survivingNodes = new Set(afterFirstLevel.nodes.map(row => row.client_key));
  const impactedNodes = new Set([...beforeParticipation].filter(([, members]) => [...members].some(key => deletedMembers.has(key))).map(([key]) => key));
  const newlyUnattached = [];
  for (const [kind, collection] of [["SUPPORT", "supports"], ["NODE_LOAD", "node_loads"]]) {
    for (const row of afterFirstLevel[collection]) {
      const key = row.target_node_client_key;
      if (impactedNodes.has(key) && survivingNodes.has(key) && beforeParticipation.has(key) && !afterParticipation.has(key)) {
        newlyUnattached.push({ kind, clientKey: row.client_key });
      }
    }
  }
  // This second level contains only leaf objects: their removal changes no topology.
  const related = unique([...directAffected, ...newlyUnattached]);
  const finalDeleteSet = unique([...selected, ...related]);
  return { selected, directAffected, newlyUnattached, finalDeleteSet,
    summary: { selected: counts(selected), related: counts(related), total: counts(finalDeleteSet) } };
}
