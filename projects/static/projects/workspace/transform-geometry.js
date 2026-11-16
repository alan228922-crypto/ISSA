import { memberParticipationByNode } from './draft-topology.js';

function fail(code) { const error = new Error(code); error.code = code; throw error; }
const finite = value => typeof value === 'number' && Number.isFinite(value);

export function captureMemberGroup(draft, keys) {
  if (draft.schema_version !== 'physical-draft-v2' || !Array.isArray(keys) || !keys.length) fail('TRANSFORM_SELECTION_REQUIRED');
  const selected = new Set(keys);
  const members = draft.physical_members.filter(row => selected.has(row.client_key));
  if (members.length !== selected.size) fail('EDITOR_TARGET_NOT_FOUND');
  const endpointKeys = new Set(members.flatMap(row => [row.start_node_client_key, row.end_node_client_key]));
  const incidences = draft.member_joint_incidences.filter(row => selected.has(row.member_client_key));
  const nodeKeys = new Set([...endpointKeys, ...incidences.map(row => row.node_client_key)]);
  const nodes = draft.nodes.filter(row => nodeKeys.has(row.client_key));
  if (nodeKeys.has(null) || nodes.length !== nodeKeys.size || nodes.some(row => !finite(row.x_mm) || !finite(row.y_mm)) || members.some(row => !Number.isInteger(row.material_id) || row.material_id <= 0 || !Number.isInteger(row.section_id) || row.section_id <= 0)) fail('TRANSFORM_INCOMPLETE_GROUP');
  return Object.freeze({ nodes: Object.freeze(nodes.map(row => Object.freeze({ ...row }))), members: Object.freeze(members.map(row => Object.freeze({ ...row }))), incidences: Object.freeze(incidences.map(row => Object.freeze({ ...row }))), endpointKeys: Object.freeze([...endpointKeys]) });
}

export function pasteMemberGroup(draft, group, offset, resources) {
  if (!group?.members?.length || !finite(offset?.x) || !finite(offset?.y)) fail('TRANSFORM_INVALID_VALUE');
  if (!resources || group.members.some(row => !resources.materialIds.includes(row.material_id) || !resources.sectionIds.includes(row.section_id))) fail('TRANSFORM_RESOURCE_UNAVAILABLE');
  const allocate = (rows, prefix) => {
    const used = new Set(rows.map(row => row.client_key)); let index = 0;
    return () => { let key; do { key = `${prefix}-${++index}`; } while (used.has(key)); used.add(key); return key; };
  };
  const nextNode = allocate(draft.nodes, 'node'), nextMember = allocate(draft.physical_members, 'member');
  const nodeMap = new Map(group.nodes.map(row => [row.client_key, nextNode()]));
  const memberMap = new Map(group.members.map(row => [row.client_key, nextMember()]));
  const nodes = group.nodes.map(row => {
    const x_mm = row.x_mm + offset.x, y_mm = row.y_mm + offset.y;
    if (!finite(x_mm) || !finite(y_mm)) fail('TRANSFORM_INVALID_VALUE');
    return { ...row, client_key: nodeMap.get(row.client_key), x_mm, y_mm };
  });
  const members = group.members.map(row => {
    const start = nodeMap.get(row.start_node_client_key), end = nodeMap.get(row.end_node_client_key);
    if (!start || !end) fail('TRANSFORM_INCOMPLETE_GROUP');
    return { ...row, client_key: memberMap.get(row.client_key), start_node_client_key: start, end_node_client_key: end };
  });
  const incidences = group.incidences.map(row => {
    const member = memberMap.get(row.member_client_key), node = nodeMap.get(row.node_client_key);
    if (!member || !node) fail('TRANSFORM_INCOMPLETE_GROUP');
    return { member_client_key: member, node_client_key: node };
  });
  // No inference, attachment cloning or mutation: the v2 editor validates the whole proposal.
  return { ...draft, nodes: [...draft.nodes, ...nodes], physical_members: [...draft.physical_members, ...members], member_joint_incidences: [...draft.member_joint_incidences, ...incidences] };
}

export function transformMemberGroup(draft, keys, transform) {
  const group = captureMemberGroup(draft, keys), selected = new Set(keys);
  const participation = memberParticipationByNode(draft);
  if (group.nodes.some(row => [...(participation.get(row.client_key) || [])].some(key => !selected.has(key)))) fail('TRANSFORM_SHARED_NODE');
  const translate = transform?.kind === 'TRANSLATE';
  if (translate ? !finite(transform.dx) || !finite(transform.dy) : transform?.kind !== 'ROTATE' || !finite(transform.angle)) fail('TRANSFORM_INVALID_VALUE');
  const endpoints = group.nodes.filter(row => group.endpointKeys.includes(row.client_key));
  if (transform.center !== undefined && (!finite(transform.center?.x) || !finite(transform.center?.y))) fail('TRANSFORM_INVALID_VALUE');
  const pivot = transform.center || endpoints.reduce((p, row) => ({ x: p.x + row.x_mm / endpoints.length, y: p.y + row.y_mm / endpoints.length }), { x: 0, y: 0 });
  const radians = translate ? 0 : (transform.angle % 360) * Math.PI / 180;
  const cos = Math.cos(radians), sin = Math.sin(radians);
  const changed = new Map(group.nodes.map(row => {
    const x_mm = translate ? row.x_mm + transform.dx : pivot.x + (row.x_mm - pivot.x) * cos - (row.y_mm - pivot.y) * sin;
    const y_mm = translate ? row.y_mm + transform.dy : pivot.y + (row.x_mm - pivot.x) * sin + (row.y_mm - pivot.y) * cos;
    if (!finite(x_mm) || !finite(y_mm)) fail('TRANSFORM_INVALID_VALUE');
    return [row.client_key, { ...row, x_mm, y_mm }];
  }));
  return { ...draft, nodes: draft.nodes.map(row => changed.get(row.client_key) || row) };
}

export function resizeMember(draft, { memberKey, nodeKey, mode, value }) {
  const member = draft.physical_members.find(row => row.client_key === memberKey);
  if (!member || ![member.start_node_client_key, member.end_node_client_key].includes(nodeKey)) fail('TRANSFORM_INCOMPLETE_GROUP');
  const moving = draft.nodes.find(row => row.client_key === nodeKey);
  const fixed = draft.nodes.find(row => row.client_key === (member.start_node_client_key === nodeKey ? member.end_node_client_key : member.start_node_client_key));
  if (!moving || !fixed || !['TOTAL', 'DELTA'].includes(mode) || !finite(value)) fail('TRANSFORM_INVALID_VALUE');
  const dx = moving.x_mm-fixed.x_mm, dy = moving.y_mm-fixed.y_mm, oldLength = Math.hypot(dx,dy);
  const length = mode === 'DELTA' ? oldLength+value : value;
  if (!finite(oldLength) || oldLength <= 0 || !finite(length) || length <= 0) fail('TRANSFORM_INVALID_VALUE');
  const x_mm = fixed.x_mm+dx/oldLength*length, y_mm = fixed.y_mm+dy/oldLength*length;
  if (!finite(x_mm) || !finite(y_mm)) fail('TRANSFORM_INVALID_VALUE');
  return { ...draft, nodes: draft.nodes.map(row => row.client_key === nodeKey ? { ...row, x_mm, y_mm } : row) };
}
