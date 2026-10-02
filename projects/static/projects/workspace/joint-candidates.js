// Geometry discovers candidates only. Confirmed editor actions own the topology.
const cache = new WeakMap();

function index(draft) {
  if (cache.has(draft)) return cache.get(draft);
  const nodes = new Map(draft.nodes.map(node => [node.client_key, node]));
  const segments = (draft.physical_members || []).flatMap(member => {
    const first = nodes.get(member.start_node_client_key); const last = nodes.get(member.end_node_client_key);
    return first && last ? [{ member, first, last, minX: Math.min(first.x_mm, last.x_mm), maxX: Math.max(first.x_mm, last.x_mm) }] : [];
  }).sort((a, b) => a.minX - b.minX);
  const result = { nodes: [...nodes.values()].sort((a, b) => a.x_mm - b.x_mm), segments };
  cache.set(draft, result);
  return result;
}

export function segmentParameter(point, first, last) {
  const dx = last.x_mm - first.x_mm; const dy = last.y_mm - first.y_mm;
  const length = Math.hypot(dx, dy);
  if (!length) return null;
  const cross = (point.x_mm - first.x_mm) * dy - (point.y_mm - first.y_mm) * dx;
  if (Math.abs(cross) > 1e-9 * Math.max(1, length)) return null;
  const t = ((point.x_mm - first.x_mm) * dx + (point.y_mm - first.y_mm) * dy) / (length * length);
  return t >= -1e-12 && t <= 1 + 1e-12 ? t : null;
}

export function candidateMembersAtNode(draft, point) {
  const hits = [];
  for (const row of index(draft).segments) {
    if (row.minX > point.x_mm + 1e-9) break;
    if (row.maxX < point.x_mm - 1e-9 || point.y_mm < Math.min(row.first.y_mm, row.last.y_mm) - 1e-9 || point.y_mm > Math.max(row.first.y_mm, row.last.y_mm) + 1e-9) continue;
    if (segmentParameter(point, row.first, row.last) !== null) hits.push(row.member.client_key);
  }
  return hits.sort();
}

export function nodesOnMember(draft, start, end) {
  return index(draft).nodes.filter(node => node.x_mm >= Math.min(start.x_mm, end.x_mm) - 1e-9 && node.x_mm <= Math.max(start.x_mm, end.x_mm) + 1e-9 && segmentParameter(node, start, end) !== null).map(node => node.client_key);
}

// Discovery is feedback/validation only, never an identity-selection rule.
export function inspectEndpointCandidates(draft, endpoint) {
  const p=endpoint.worldPoint;
  return {
    passingMemberClientKeys:candidateMembersAtNode(draft,{x_mm:p.x,y_mm:p.y}),
    collocatedNodeClientKeys:draft.nodes.filter(n=>n.x_mm===p.x&&n.y_mm===p.y).map(n=>n.client_key),
  };
}
