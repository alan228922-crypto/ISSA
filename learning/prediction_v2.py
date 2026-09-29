"""Prediction-v2 references explicit structural Node identities."""

from modeling.topology import ordered_member_nodes


def validate_prediction_v2(project, payload):
    from .services import PredictionError, _member_judgments

    def invalid(code="PREDICTION_INVALID_SCHEMA"):
        raise PredictionError(code, 400)

    if not isinstance(payload, dict) or payload.get("schema_version") != "prediction-v2" or set(payload) != {"schema_version", "member_judgments", "max_displacement_location", "representative_load_path"}:
        invalid()
    _member_judgments(project, payload)
    nodes = {row.client_key: (row.x_mm, row.y_mm) for row in project.geometry_nodes.all()}
    members = {
        row.client_key: {"client_key": row.client_key, "start_node_client_key": row.start_geometry_node.client_key if row.start_geometry_node_id else None, "end_node_client_key": row.end_geometry_node.client_key if row.end_geometry_node_id else None}
        for row in project.physical_members.select_related("start_geometry_node", "end_geometry_node")
    }
    incidences = set(project.member_joint_incidences.values_list("member__client_key", "node__client_key"))
    location = payload["max_displacement_location"]
    if not isinstance(location, dict) or set(location) != {"kind", "node_client_key"} or location.get("kind") != "NODE" or location.get("node_client_key") not in nodes:
        invalid("INVALID_PHYSICAL_POINT_REF")
    path = payload["representative_load_path"]
    if not isinstance(path, list) or len(path) < 3 or len(path) % 2 != 1:
        invalid("INVALID_LOAD_PATH")
    identities = []
    for position, entry in enumerate(path):
        kind = "NODE" if position % 2 == 0 else "PHYSICAL_MEMBER"
        field = "node_client_key" if kind == "NODE" else "physical_member_client_key"
        if not isinstance(entry, dict) or set(entry) != {"kind", field} or entry.get("kind") != kind:
            invalid("INVALID_LOAD_PATH")
        key = entry.get(field)
        if not isinstance(key, str) or key not in (nodes if kind == "NODE" else members):
            invalid("INVALID_LOAD_PATH")
        identities.append((kind, key))
    if len(identities) != len(set(identities)):
        invalid("INVALID_LOAD_PATH")
    for position in range(1, len(identities), 2):
        member = members[identities[position][1]]
        try:
            ordered = ordered_member_nodes(member, nodes, incidences)
        except (KeyError, ValueError):
            invalid("INVALID_LOAD_PATH")
        first, last = identities[position - 1][1], identities[position + 1][1]
        if not any((left, right) == (first, last) or (left, right) == (last, first) for left, right in zip(ordered, ordered[1:])):
            invalid("INVALID_LOAD_PATH")
    return payload
