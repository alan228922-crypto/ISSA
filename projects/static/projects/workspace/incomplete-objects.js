const KINDS = Object.freeze({
  PHYSICAL_MEMBER: { collection: "physical_members", name: "构件" },
  CONNECTION: { collection: "connections", name: "连接" },
  SUPPORT: { collection: "supports", name: "支座" },
  NODE_LOAD: { collection: "node_loads", name: "荷载" },
});

export const MISSING_FIELD_NAMES = Object.freeze({
  MISSING_MEMBER_START_NODE: "起点",
  MISSING_MEMBER_END_NODE: "终点",
  MISSING_MEMBER_MATERIAL: "材料",
  MISSING_MEMBER_SECTION: "截面",
  MISSING_CONNECTION_NODE: "位置节点",
  MISSING_CONNECTION_PARTICIPANT: "参与构件",
  MISSING_SUPPORT_NODE: "作用位置",
  MISSING_LOAD_NODE: "作用位置",
});

export function studentObjectName(draft, kind, key) {
  const definition = KINDS[kind];
  if (!definition) return "物件";
  const records = [...(draft[definition.collection] || [])].sort((a, b) => a.client_key.localeCompare(b.client_key, undefined, { numeric: true }));
  const index = records.findIndex((record) => record.client_key === key);
  const label = records[index]?.label?.trim();
  return `${definition.name} ${label || (index < 0 ? "" : index + 1)}`.trim();
}

export function incompleteDraftObjects(draft) {
  const result = [];
  const nodes = new Set((draft.nodes || []).map((item) => item.client_key));
  const members = new Set((draft.physical_members || []).map((item) => item.client_key));
  const connectionByKey = new Map((draft.connections || []).map((item) => [item.client_key, item]));
  const collect = (kind, record, codes) => {
    if (codes.length) result.push({ kind, clientKey: record.client_key, name: studentObjectName(draft, kind, record.client_key), fields: codes.map((code) => MISSING_FIELD_NAMES[code]) });
  };
  for (const record of draft.physical_members || []) {
    const codes = [];
    if (!nodes.has(record.start_node_client_key)) codes.push("MISSING_MEMBER_START_NODE");
    if (!nodes.has(record.end_node_client_key)) codes.push("MISSING_MEMBER_END_NODE");
    if (record.material_id == null) codes.push("MISSING_MEMBER_MATERIAL");
    if (record.section_id == null) codes.push("MISSING_MEMBER_SECTION");
    collect("PHYSICAL_MEMBER", record, codes);
  }
  for (const record of draft.connections || []) {
    const codes = [];
    if (!nodes.has(record.geometry_node_client_key)) codes.push("MISSING_CONNECTION_NODE");
    if ((record.participating_member_client_keys || []).some((key) => !members.has(key))) codes.push("MISSING_CONNECTION_PARTICIPANT");
    collect("CONNECTION", record, codes);
  }
  const hasLocation = (key) => nodes.has(connectionByKey.get(key)?.geometry_node_client_key);
  for (const record of draft.supports || []) if (!hasLocation(record.target_connection_client_key)) collect("SUPPORT", record, ["MISSING_SUPPORT_NODE"]);
  for (const record of draft.node_loads || []) if (!hasLocation(record.target_connection_client_key)) collect("NODE_LOAD", record, ["MISSING_LOAD_NODE"]);
  return result.sort((a, b) => a.kind === b.kind ? a.clientKey.localeCompare(b.clientKey, undefined, { numeric: true }) : 0);
}

export function groupDraftCheckIssues(draft, issues) {
  const grouped = new Map();
  const other = [];
  for (const issue of issues) {
    const target = issue.physical_object;
    if (!MISSING_FIELD_NAMES[issue.code] || !KINDS[target?.kind] || !target.client_key) { other.push(issue); continue; }
    const id = `${target.kind}:${target.client_key}`;
    if (!grouped.has(id)) grouped.set(id, { kind: target.kind, clientKey: target.client_key, name: studentObjectName(draft, target.kind, target.client_key), fields: [], issue });
    const field = MISSING_FIELD_NAMES[issue.code];
    if (!grouped.get(id).fields.includes(field)) grouped.get(id).fields.push(field);
  }
  return { objects: [...grouped.values()].sort((a, b) => a.kind === b.kind ? a.clientKey.localeCompare(b.clientKey, undefined, { numeric: true }) : 0), other };
}
