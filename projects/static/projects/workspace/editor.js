const COLLECTIONS = {
  GEOMETRY_NODE: "nodes",
  PHYSICAL_MEMBER: "physical_members",
  CONNECTION: "connections",
  SUPPORT: "supports",
  NODE_LOAD: "node_loads",
};

const UPDATE_FIELDS = {
  GEOMETRY_NODE: new Set(["x_mm", "y_mm", "label"]),
  PHYSICAL_MEMBER: new Set(["material_id", "section_id", "label", "is_active"]),
  SUPPORT: new Set(["support_type", "restrained_axis"]),
  NODE_LOAD: new Set(["fx_N", "fy_N", "label"]),
};

const FIELDS = {
  GEOMETRY_NODE: ["client_key", "x_mm", "y_mm", "label"],
  PHYSICAL_MEMBER: ["client_key", "start_node_client_key", "end_node_client_key", "material_id", "section_id", "label", "is_active"],
  CONNECTION: ["client_key", "geometry_node_client_key", "participating_member_client_keys"],
  SUPPORT: ["client_key", "target_connection_client_key", "support_type", "restrained_axis"],
  NODE_LOAD: ["client_key", "target_connection_client_key", "fx_N", "fy_N", "label"],
};

export class EditorActionError extends Error {
  constructor(code) {
    super(code);
    this.name = "EditorActionError";
    this.code = code;
  }
}

function fail(code) {
  throw new EditorActionError(code);
}

function object(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function key(value) {
  return typeof value === "string" && value.length > 0;
}

function collection(draft, kind) {
  const name = COLLECTIONS[kind];
  if (!name || !Array.isArray(draft?.[name])) fail("EDITOR_INVALID_ACTION");
  return [name, draft[name]];
}

function has(items, clientKey) {
  return items.some((item) => item.client_key === clientKey);
}

function requireObject(kind, value) {
  const fields = FIELDS[kind];
  if (!fields || !object(value) || !key(value.client_key) || Object.keys(value).length !== fields.length || !fields.every((field) => Object.hasOwn(value, field))) fail("EDITOR_INVALID_ACTION");
}

function add(draft, kind, value) {
  requireObject(kind, value);
  const [name, items] = collection(draft, kind);
  if (has(items, value.client_key)) fail("EDITOR_DUPLICATE_CLIENT_KEY");
  const next = kind === "CONNECTION" ? {...value, participating_member_client_keys: [...value.participating_member_client_keys]} : {...value};
  return {...draft, [name]: [...items, next]};
}

function nodes(draft, keys) {
  return keys.every((clientKey) => key(clientKey) && has(draft.nodes, clientKey));
}

function members(draft, keys) {
  return keys.every((clientKey) => key(clientKey) && has(draft.physical_members, clientKey));
}

function pointOnMember(draft, node, member) {
  const start = draft.nodes.find((item) => item.client_key === member.start_node_client_key);
  const end = draft.nodes.find((item) => item.client_key === member.end_node_client_key);
  if (!start || !end) return false;
  const dx = end.x_mm - start.x_mm; const dy = end.y_mm - start.y_mm;
  const px = node.x_mm - start.x_mm; const py = node.y_mm - start.y_mm;
  const length = Math.hypot(dx, dy);
  if (!length) return false;
  const distance = Math.abs(dx * py - dy * px) / length;
  const position = (px * dx + py * dy) / (length * length);
  return distance <= 1e-9 && position >= -1e-12 && position <= 1 + 1e-12;
}

function nextConnectionKey(draft) {
  const keys = new Set(draft.connections.map((item) => item.client_key));
  let index = 1;
  while (keys.has(`connection-${index}`)) index += 1;
  return `connection-${index}`;
}

function connectNode(draft, node) {
  const participants = draft.physical_members.filter((member) => pointOnMember(draft, node, member)).map((member) => member.client_key);
  if (!participants.length) return draft;
  const existing = draft.connections.find((connection) => connection.geometry_node_client_key === node.client_key);
  if (existing) {
    const merged = [...new Set([...existing.participating_member_client_keys, ...participants])].sort();
    if (merged.length === existing.participating_member_client_keys.length) return draft;
    return { ...draft, connections: draft.connections.map((connection) => connection === existing ? { ...connection, participating_member_client_keys: merged } : connection) };
  }
  return createConnection(draft, { client_key: nextConnectionKey(draft), geometry_node_client_key: node.client_key, participating_member_client_keys: participants.sort() });
}

export function resolveNodeConnection(draft, nodeClientKey) {
  const node = draft.nodes.find((item) => item.client_key === nodeClientKey);
  if (!node) fail("EDITOR_TARGET_NOT_FOUND");
  const existing = draft.connections.filter((item) => item.geometry_node_client_key === nodeClientKey);
  if (existing.length > 1) fail("MULTIPLE_JOINTS_AT_NODE");
  if (!draft.physical_members.some((member) => pointOnMember(draft, node, member))) fail("NODE_NOT_ON_MEMBER");
  const next = existing.length ? draft : connectNode(draft, node);
  return { draft: next, connectionClientKey: next.connections.find((item) => item.geometry_node_client_key === nodeClientKey).client_key };
}

function createMember(draft, member) {
  requireObject("PHYSICAL_MEMBER", member);
  if (!nodes(draft, [member.start_node_client_key, member.end_node_client_key])) fail("EDITOR_REFERENCE_NOT_FOUND");
  let next = add(draft, "PHYSICAL_MEMBER", member);
  for (const node of next.nodes) if (pointOnMember(next, node, member)) next = connectNode(next, node);
  return next;
}

function createConnection(draft, connection) {
  requireObject("CONNECTION", connection);
  const keys = connection.participating_member_client_keys;
  if (!key(connection.geometry_node_client_key) || !Array.isArray(keys) || keys.length === 0) fail("EDITOR_INVALID_ACTION");
  if (!nodes(draft, [connection.geometry_node_client_key]) || !members(draft, keys)) fail("EDITOR_REFERENCE_NOT_FOUND");
  if (new Set(keys).size !== keys.length || keys.some((value, index) => index > 0 && keys[index - 1] >= value)) fail("EDITOR_INVALID_ACTION");
  return add(draft, "CONNECTION", {...connection, participating_member_client_keys: [...keys]});
}

function createReferenced(draft, kind, value) {
  requireObject(kind, value);
  if (!key(value.target_connection_client_key) || !has(draft.connections, value.target_connection_client_key)) fail("EDITOR_REFERENCE_NOT_FOUND");
  return add(draft, kind, value);
}

function update(draft, action) {
  if (!object(action.target) || !key(action.target.clientKey) || !object(action.changes)) fail("EDITOR_INVALID_ACTION");
  const {kind, clientKey} = action.target;
  if (!Object.hasOwn(COLLECTIONS, kind)) fail("EDITOR_INVALID_ACTION");
  if (kind === "CONNECTION") fail("EDITOR_UPDATE_FIELD_NOT_ALLOWED");
  const allowed = UPDATE_FIELDS[kind];
  if (!allowed || Object.keys(action.changes).some((field) => !allowed.has(field))) fail("EDITOR_UPDATE_FIELD_NOT_ALLOWED");
  const [name, items] = collection(draft, kind);
  const index = items.findIndex((item) => item.client_key === clientKey);
  if (index < 0) fail("EDITOR_TARGET_NOT_FOUND");
  return {...draft, [name]: items.map((item, itemIndex) => itemIndex === index ? {...item, ...action.changes} : item)};
}

function referenced(draft, kind, clientKey) {
  if (kind === "GEOMETRY_NODE") return draft.physical_members.some((member) => member.start_node_client_key === clientKey || member.end_node_client_key === clientKey) || draft.connections.some((connection) => connection.geometry_node_client_key === clientKey);
  if (kind === "PHYSICAL_MEMBER") return draft.connections.some((connection) => connection.participating_member_client_keys.includes(clientKey));
  if (kind === "CONNECTION") return draft.supports.some((support) => support.target_connection_client_key === clientKey) || draft.node_loads.some((load) => load.target_connection_client_key === clientKey);
  return false;
}

function remove(draft, action) {
  if (!object(action.target) || !key(action.target.clientKey)) fail("EDITOR_INVALID_ACTION");
  const {kind, clientKey} = action.target;
  const [name, items] = collection(draft, kind);
  if (!has(items, clientKey)) fail("EDITOR_TARGET_NOT_FOUND");
  if (referenced(draft, kind, clientKey)) fail("EDITOR_DEPENDENCY_CONFLICT");
  return {...draft, [name]: items.filter((item) => item.client_key !== clientKey)};
}

function deleteObjectsAtomically(draft, targets) {
  if (!Array.isArray(targets) || !targets.length) fail("EDITOR_INVALID_ACTION");
  const removed = Object.fromEntries(Object.keys(COLLECTIONS).map((kind) => [kind, new Set()]));
  for (const target of targets) {
    if (!object(target) || !key(target.clientKey)) fail("EDITOR_INVALID_ACTION");
    const [, items] = collection(draft, target.kind);
    if (!has(items, target.clientKey)) fail("EDITOR_TARGET_NOT_FOUND");
    removed[target.kind].add(target.clientKey);
  }
  const nodes = draft.nodes.filter((item) => !removed.GEOMETRY_NODE.has(item.client_key));
  const physical_members = draft.physical_members.filter((item) => !removed.PHYSICAL_MEMBER.has(item.client_key));
  if (physical_members.some((member) => !nodes.some((node) => node.client_key === member.start_node_client_key) || !nodes.some((node) => node.client_key === member.end_node_client_key))) fail("EDITOR_DEPENDENCY_CONFLICT");
  const survivingMemberKeys = new Set(physical_members.map((member) => member.client_key));
  if (draft.connections.some((item) => removed.CONNECTION.has(item.client_key) && item.participating_member_client_keys.some((memberKey) => survivingMemberKeys.has(memberKey)))) fail("EDITOR_DEPENDENCY_CONFLICT");
  const connections = draft.connections.filter((item) => !removed.CONNECTION.has(item.client_key)).map((item) => ({ ...item, participating_member_client_keys: item.participating_member_client_keys.filter((memberKey) => survivingMemberKeys.has(memberKey)) })).filter((item) => item.participating_member_client_keys.length);
  if (connections.some((connection) => !nodes.some((node) => node.client_key === connection.geometry_node_client_key))) fail("EDITOR_DEPENDENCY_CONFLICT");
  const connectionKeys = new Set(connections.map((item) => item.client_key));
  const supports = draft.supports.filter((item) => !removed.SUPPORT.has(item.client_key));
  const node_loads = draft.node_loads.filter((item) => !removed.NODE_LOAD.has(item.client_key));
  if ([...supports, ...node_loads].some((item) => !connectionKeys.has(item.target_connection_client_key))) fail("EDITOR_DEPENDENCY_CONFLICT");
  return { ...draft, nodes, physical_members, connections, supports, node_loads };
}

export function applyEditorAction(draft, action) {
  if (!object(draft) || !object(action)) fail("EDITOR_INVALID_ACTION");
  switch (action.type) {
    case "CREATE_NODE": return add(draft, "GEOMETRY_NODE", action.node);
    case "PLACE_JOINT_NODE": {
      const existing = draft.nodes.find((item) => Math.abs(item.x_mm - action.node?.x_mm) < 1e-9 && Math.abs(item.y_mm - action.node?.y_mm) < 1e-9);
      if (existing) return connectNode(draft, existing);
      const next = add(draft, "GEOMETRY_NODE", action.node);
      return connectNode(next, action.node);
    }
    case "CONNECT_NODE": {
      const node = draft.nodes.find((item) => item.client_key === action.nodeClientKey);
      if (!node) fail("EDITOR_TARGET_NOT_FOUND");
      return connectNode(draft, node);
    }
    case "CREATE_MEMBER": return createMember(draft, action.member);
    case "CREATE_CONNECTION": return createConnection(draft, action.connection);
    case "CREATE_SUPPORT": return createReferenced(draft, "SUPPORT", action.support);
    case "CREATE_NODE_LOAD": return createReferenced(draft, "NODE_LOAD", action.nodeLoad);
    case "CREATE_SUPPORT_AT_NODE": {
      const resolved = resolveNodeConnection(draft, action.nodeClientKey);
      return createReferenced(resolved.draft, "SUPPORT", { ...action.support, target_connection_client_key: resolved.connectionClientKey });
    }
    case "CREATE_NODE_LOAD_AT_NODE": {
      const resolved = resolveNodeConnection(draft, action.nodeClientKey);
      return createReferenced(resolved.draft, "NODE_LOAD", { ...action.nodeLoad, target_connection_client_key: resolved.connectionClientKey });
    }
    case "UPDATE_OBJECT": return update(draft, action);
    case "DELETE_OBJECTS": return deleteObjectsAtomically(draft, action.targets);
    case "DELETE_OBJECT": return deleteObjectsAtomically(draft, [action.target]);
    default: return fail("EDITOR_INVALID_ACTION");
  }
}
