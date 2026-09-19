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

function createMember(draft, member) {
  requireObject("PHYSICAL_MEMBER", member);
  if (!nodes(draft, [member.start_node_client_key, member.end_node_client_key])) fail("EDITOR_REFERENCE_NOT_FOUND");
  return add(draft, "PHYSICAL_MEMBER", member);
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

export function applyEditorAction(draft, action) {
  if (!object(draft) || !object(action)) fail("EDITOR_INVALID_ACTION");
  switch (action.type) {
    case "CREATE_NODE": return add(draft, "GEOMETRY_NODE", action.node);
    case "CREATE_MEMBER": return createMember(draft, action.member);
    case "CREATE_CONNECTION": return createConnection(draft, action.connection);
    case "CREATE_SUPPORT": return createReferenced(draft, "SUPPORT", action.support);
    case "CREATE_NODE_LOAD": return createReferenced(draft, "NODE_LOAD", action.nodeLoad);
    case "UPDATE_OBJECT": return update(draft, action);
    case "DELETE_OBJECT": return remove(draft, action);
    default: return fail("EDITOR_INVALID_ACTION");
  }
}
