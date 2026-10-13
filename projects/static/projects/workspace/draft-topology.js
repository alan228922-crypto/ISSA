// Explicit relationships only. This query is not geometry or validation authority.
export function memberParticipationByNode(draft) {
  const result = new Map();
  const members = new Set(draft.physical_members.map(row => row.client_key));
  const add = (nodeKey, memberKey) => {
    if (nodeKey == null) return;
    if (!result.has(nodeKey)) result.set(nodeKey, new Set());
    result.get(nodeKey).add(memberKey);
  };
  for (const member of draft.physical_members) {
    add(member.start_node_client_key, member.client_key);
    add(member.end_node_client_key, member.client_key);
  }
  for (const pair of draft.member_joint_incidences || []) {
    if (members.has(pair.member_client_key)) add(pair.node_client_key, pair.member_client_key);
  }
  return result;
}
