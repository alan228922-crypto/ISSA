import { candidateMembersAtNode, nodesOnMember, segmentParameter } from "./joint-candidates.js";

const COLLECTIONS = { GEOMETRY_NODE: "nodes", PHYSICAL_MEMBER: "physical_members", SUPPORT: "supports", NODE_LOAD: "node_loads" };

function fail(code) { const error = new Error(code); error.code = code; throw error; }
const find = (draft, kind, key) => draft[COLLECTIONS[kind]]?.find(row => row.client_key === key);
const same = (a, b) => a.x_mm === b.x_mm && a.y_mm === b.y_mm;
const node = (draft, key) => draft.nodes.find(row => row.client_key === key);

function add(draft, kind, value) {
  if (!value || typeof value.client_key !== "string" || !value.client_key || find(draft, kind, value.client_key)) fail("EDITOR_DUPLICATE_CLIENT_KEY");
  const collection = COLLECTIONS[kind];
  return { ...draft, [collection]: [...draft[collection], { ...value }] };
}

function incidence(draft, memberKey, nodeKey) {
  if (draft.member_joint_incidences.some(row => row.member_client_key === memberKey && row.node_client_key === nodeKey)) return draft;
  return { ...draft, member_joint_incidences: [...draft.member_joint_incidences, { member_client_key: memberKey, node_client_key: nodeKey }] };
}

function authorAtNode(draft, nodeKey) {
  const target = node(draft, nodeKey);
  if (!target) fail("EDITOR_REFERENCE_NOT_FOUND");
  let next = draft;
  for (const memberKey of candidateMembersAtNode(draft, target)) {
    const member = find(draft, "PHYSICAL_MEMBER", memberKey);
    if ([member.start_node_client_key, member.end_node_client_key].includes(nodeKey)) continue;
    const first = node(draft, member.start_node_client_key); const last = node(draft, member.end_node_client_key);
    const t = segmentParameter(target, first, last);
    if (t <= 1e-12 || t >= 1 - 1e-12) fail("EDITOR_AMBIGUOUS_JOINT_IDENTITY");
    next = incidence(next, memberKey, nodeKey);
  }
  return next;
}

function placeNode(draft, value) {
  if (!value || !Number.isFinite(value.x_mm) || !Number.isFinite(value.y_mm)) fail("EDITOR_INVALID_ACTION");
  const existing = draft.nodes.filter(row => same(row, value));
  if (existing.length > 1) fail("EDITOR_AMBIGUOUS_JOINT_IDENTITY");
  const next = existing.length ? draft : add(draft, "GEOMETRY_NODE", value);
  return authorAtNode(next, existing[0]?.client_key || value.client_key);
}

function createMember(draft, value) {
  if (!value || ![value.start_node_client_key, value.end_node_client_key].every(key => key === null || node(draft, key))) fail("EDITOR_REFERENCE_NOT_FOUND");
  let next = add(draft, "PHYSICAL_MEMBER", value);
  const first = node(next, value.start_node_client_key); const last = node(next, value.end_node_client_key);
  if (!first || !last) return next;
  for (const nodeKey of nodesOnMember(next, first, last)) {
    if (nodeKey === value.start_node_client_key || nodeKey === value.end_node_client_key) continue;
    const target = node(next, nodeKey); const t = segmentParameter(target, first, last);
    if (t <= 1e-12 || t >= 1 - 1e-12) fail("EDITOR_AMBIGUOUS_JOINT_IDENTITY");
    next = incidence(next, value.client_key, nodeKey);
  }
  return next;
}

function structuralIssues(draft) {
  const issues = new Set();
  for (let i = 0; i < draft.nodes.length; i++) for (let j = i + 1; j < draft.nodes.length; j++) {
    if (same(draft.nodes[i], draft.nodes[j])) issues.add(`PAIR:${[draft.nodes[i].client_key, draft.nodes[j].client_key].sort().join(":")}:${draft.nodes[i].x_mm}:${draft.nodes[i].y_mm}`);
  }
  for (const member of draft.physical_members) {
    const first = node(draft, member.start_node_client_key); const last = node(draft, member.end_node_client_key);
    if (!first || !last) continue;
    if (same(first, last)) issues.add(`ZERO:${member.client_key}`);
    const rows = draft.member_joint_incidences.filter(row => row.member_client_key === member.client_key);
    const positions = [0, 1];
    for (const row of rows) {
      const target = node(draft, row.node_client_key);
      const t = target && segmentParameter(target, first, last);
      if (t === null || t <= 1e-12 || t >= 1 - 1e-12) issues.add(`INCIDENCE:${member.client_key}:${row.node_client_key}`);
      else positions.push(t);
    }
    positions.sort((a, b) => a - b);
    if (positions.some((value, index) => index && value - positions[index - 1] <= 1e-12)) issues.add(`SEGMENT:${member.client_key}`);
    for (const nodeKey of nodesOnMember(draft, first, last)) {
      if ([member.start_node_client_key, member.end_node_client_key].includes(nodeKey) || rows.some(row => row.node_client_key === nodeKey)) continue;
      const target = node(draft, nodeKey);
      issues.add(`PASS:${member.client_key}:${nodeKey}:${target.x_mm}:${target.y_mm}:${first.x_mm}:${first.y_mm}:${last.x_mm}:${last.y_mm}`);
    }
  }
  return issues;
}

function validate(draft, previous) {
  const oldIssues = structuralIssues(previous);
  for (const issue of structuralIssues(draft)) if (!oldIssues.has(issue)) fail(issue.startsWith("PASS:") ? "MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE" : "EDITOR_INVALID_TOPOLOGY");
  return draft;
}

function update(draft, target, changes) {
  const collection = COLLECTIONS[target?.kind];
  if (!collection || !find(draft, target.kind, target.clientKey) || !changes || "client_key" in changes) fail("EDITOR_INVALID_ACTION");
  for (const field of ["start_node_client_key", "end_node_client_key", "target_node_client_key"]) if (field in changes && changes[field] !== null && !node(draft, changes[field])) fail("EDITOR_REFERENCE_NOT_FOUND");
  let next = { ...draft, [collection]: draft[collection].map(row => row.client_key === target.clientKey ? { ...row, ...changes } : row) };
  if (target.kind === "PHYSICAL_MEMBER" && ("start_node_client_key" in changes || "end_node_client_key" in changes)) {
    next = { ...next, member_joint_incidences: next.member_joint_incidences.filter(row => row.member_client_key !== target.clientKey) };
    const changed = find(next, "PHYSICAL_MEMBER", target.clientKey);
    next = { ...next, physical_members: next.physical_members.filter(row => row.client_key !== target.clientKey) };
    next = createMember(next, changed);
  }
  return validate(next, draft);
}

function remove(draft, targets) {
  if (!Array.isArray(targets) || !targets.length) fail("EDITOR_INVALID_ACTION");
  const deleted = Object.fromEntries(Object.keys(COLLECTIONS).map(kind => [kind, new Set()]));
  for (const target of targets) {
    if (!COLLECTIONS[target?.kind] || !find(draft, target.kind, target.clientKey)) fail("EDITOR_TARGET_NOT_FOUND");
    deleted[target.kind].add(target.clientKey);
  }
  const nodes = draft.nodes.filter(row => !deleted.GEOMETRY_NODE.has(row.client_key));
  const physical_members = draft.physical_members.filter(row => !deleted.PHYSICAL_MEMBER.has(row.client_key)).map(row => ({ ...row,
    start_node_client_key: deleted.GEOMETRY_NODE.has(row.start_node_client_key) ? null : row.start_node_client_key,
    end_node_client_key: deleted.GEOMETRY_NODE.has(row.end_node_client_key) ? null : row.end_node_client_key,
  }));
  const member_joint_incidences = draft.member_joint_incidences.filter(row => !deleted.PHYSICAL_MEMBER.has(row.member_client_key) && !deleted.GEOMETRY_NODE.has(row.node_client_key));
  const supports = draft.supports.filter(row => !deleted.SUPPORT.has(row.client_key)).map(row => ({ ...row, target_node_client_key: deleted.GEOMETRY_NODE.has(row.target_node_client_key) ? null : row.target_node_client_key }));
  const node_loads = draft.node_loads.filter(row => !deleted.NODE_LOAD.has(row.client_key)).map(row => ({ ...row, target_node_client_key: deleted.GEOMETRY_NODE.has(row.target_node_client_key) ? null : row.target_node_client_key }));
  return { ...draft, nodes, physical_members, member_joint_incidences, supports, node_loads };
}

export function applyEditorActionV2(draft, action) {
  let next;
  switch (action?.type) {
    case "CREATE_NODE": case "PLACE_JOINT_NODE": next = placeNode(draft, action.node); break;
    case "CONNECT_NODE": next = authorAtNode(draft, action.nodeClientKey); break;
    case "CREATE_MEMBER": next = createMember(draft, action.member); break;
    case "CREATE_MEMBER_WITH_ENDPOINT": next = createMember(action.node ? placeNode(draft, action.node) : draft, action.member); break;
    case "CREATE_SUPPORT_AT_NODE": case "CREATE_NODE_LOAD_AT_NODE": {
      if (!node(draft, action.nodeClientKey)) fail("EDITOR_REFERENCE_NOT_FOUND");
      if (!draft.physical_members.some(row => [row.start_node_client_key, row.end_node_client_key].includes(action.nodeClientKey) || draft.member_joint_incidences.some(pair => pair.member_client_key === row.client_key && pair.node_client_key === action.nodeClientKey))) fail("NODE_NOT_ON_MEMBER");
      const support = action.type === "CREATE_SUPPORT_AT_NODE";
      next = add(draft, support ? "SUPPORT" : "NODE_LOAD", { ...(support ? action.support : action.nodeLoad), target_node_client_key: action.nodeClientKey }); break;
    }
    case "CREATE_SUPPORT": case "CREATE_NODE_LOAD": next = add(draft, action.type === "CREATE_SUPPORT" ? "SUPPORT" : "NODE_LOAD", action.type === "CREATE_SUPPORT" ? action.support : action.nodeLoad); break;
    case "UPDATE_OBJECT": next = update(draft, action.target, action.changes); break;
    case "DELETE_OBJECTS": next = remove(draft, action.targets); break;
    case "DELETE_OBJECT": next = remove(draft, [action.target]); break;
    default: fail("EDITOR_INVALID_ACTION");
  }
  return validate(next, draft);
}
