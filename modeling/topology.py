"""Pure, explicit v2 Node/member incidence geometry checks."""

from bisect import bisect_left, bisect_right
from math import hypot


def _parameter(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy)
    if length == 0:
        return None
    cross = (point[0] - start[0]) * dy - (point[1] - start[1]) * dx
    if abs(cross) > 1e-9 * max(1.0, length):
        return None
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (length * length)
    return t if -1e-12 <= t <= 1 + 1e-12 else None


def ordered_member_nodes(member, nodes, incidences):
    """Return the two endpoints and only the explicitly incident interior Nodes."""
    key = member["client_key"]
    first = member["start_node_client_key"]
    last = member["end_node_client_key"]
    if first is None or last is None:
        return [key for key in (first, last) if key is not None]
    if first not in nodes or last not in nodes or first == last:
        raise ValueError("INVALID_MEMBER_ENDPOINT")
    positions = [(0.0, first), (1.0, last)]
    for member_key, node_key in incidences:
        if member_key != key:
            continue
        if node_key not in nodes or node_key in (first, last):
            raise ValueError("INVALID_MEMBER_INCIDENCE")
        t = _parameter(nodes[node_key], nodes[first], nodes[last])
        if t is None or not 1e-12 < t < 1 - 1e-12:
            raise ValueError("INVALID_MEMBER_INCIDENCE")
        positions.append((t, node_key))
    positions.sort()
    if any(right[0] - left[0] <= 1e-12 for left, right in zip(positions, positions[1:])):
        raise ValueError("DUPLICATE_MEMBER_INCIDENCE_POSITION")
    return [node_key for _, node_key in positions]


def find_unrepresented_passes(*, nodes, members, incidences, exemptions):
    """Index by X, then inspect only Nodes in each member bounding box."""
    by_x = sorted((point[0], key, point) for key, point in nodes.items())
    xs = [row[0] for row in by_x]
    missing = []
    for member in members:
        first = member["start_node_client_key"]
        last = member["end_node_client_key"]
        if first is None or last is None or first not in nodes or last not in nodes:
            continue
        start, end = nodes[first], nodes[last]
        epsilon = 1e-9
        lo = bisect_left(xs, min(start[0], end[0]) - epsilon)
        hi = bisect_right(xs, max(start[0], end[0]) + epsilon)
        for _, node_key, point in by_x[lo:hi]:
            if node_key in (first, last) or (member["client_key"], node_key) in incidences or (member["client_key"], node_key) in exemptions:
                continue
            if not min(start[1], end[1]) - epsilon <= point[1] <= max(start[1], end[1]) + epsilon:
                continue
            t = _parameter(point, start, end)
            if t is not None and -1e-12 <= t <= 1 + 1e-12:
                missing.append((member["client_key"], node_key))
    return sorted(missing)
