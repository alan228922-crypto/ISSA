"""Validation for student prediction evidence; deliberately independent of mechanics."""

from modeling.models import Connection, PhysicalMember


class PredictionError(ValueError):
    def __init__(self, code, status_code=400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


_STATES = {"TENSION", "COMPRESSION", "ZERO_FORCE", "UNSURE"}


def _schema_error():
    raise PredictionError("PREDICTION_INVALID_SCHEMA", 400)


def _string(value):
    return isinstance(value, str) and bool(value)


def _only_keys(value, allowed, error):
    if not isinstance(value, dict) or set(value) - allowed:
        raise PredictionError(error, 400)


def _display(value, allowed):
    _only_keys(value, allowed, "PREDICTION_INVALID_SCHEMA")
    if any(not _string(item) for item in value.values()):
        _schema_error()


def _member_judgments(project, payload):
    judgments = payload.get("member_judgments")
    if not isinstance(judgments, list):
        _schema_error()
    keys = []
    for judgment in judgments:
        _only_keys(
            judgment,
            {"physical_member_client_key", "predicted_state", "display"},
            "PREDICTION_INVALID_SCHEMA",
        )
        if "display" in judgment:
            _display(judgment["display"], {"member_label"})
        key = judgment.get("physical_member_client_key")
        if not _string(key) or judgment.get("predicted_state") not in _STATES:
            _schema_error()
        keys.append(key)

    active_keys = set(
        PhysicalMember.objects.filter(project=project, is_active=True).values_list("client_key", flat=True)
    )
    if len(keys) != len(set(keys)) or set(keys) != active_keys:
        raise PredictionError("PREDICTION_INCOMPLETE", 400)


def _topology(project):
    members = {
        member.client_key: member
        for member in PhysicalMember.objects.filter(project=project).select_related(
            "start_geometry_node", "end_geometry_node"
        )
    }
    connections = {
        connection.client_key: connection
        for connection in Connection.objects.filter(project=project).prefetch_related("participating_members")
    }
    return members, connections


def _is_incident(connection, member):
    return (
        member in connection.participating_members.all()
        and connection.geometry_node_id in {
            member.start_geometry_node_id,
            member.end_geometry_node_id,
        }
    )


def _physical_point(point, members, connections):
    if not isinstance(point, dict):
        _schema_error()
    kind = point.get("kind")
    if kind == "CONNECTION":
        _only_keys(point, {"kind", "connection_client_key", "display"}, "PREDICTION_INVALID_SCHEMA")
        if "display" in point:
            _display(point["display"], {"geometry_node_client_key", "geometry_node_label"})
        key = point.get("connection_client_key")
        if not _string(key) or key not in connections:
            raise PredictionError("INVALID_PHYSICAL_POINT_REF", 400)
        return ("connection", key)
    if kind != "MEMBER_ENDPOINT":
        _schema_error()

    _only_keys(
        point,
        {"kind", "physical_member_client_key", "endpoint", "display"},
        "PREDICTION_INVALID_SCHEMA",
    )
    if "display" in point:
        _display(
            point["display"],
            {"member_label", "geometry_node_client_key", "geometry_node_label"},
        )
    key, endpoint = point.get("physical_member_client_key"), point.get("endpoint")
    if not _string(key) or endpoint not in {"START", "END"} or key not in members:
        raise PredictionError("INVALID_PHYSICAL_POINT_REF", 400)
    member = members[key]
    node_id = member.start_geometry_node_id if endpoint == "START" else member.end_geometry_node_id
    if any(_is_incident(connection, member) and connection.geometry_node_id == node_id for connection in connections.values()):
        raise PredictionError("INVALID_PHYSICAL_POINT_REF", 400)
    return ("free", key, endpoint)


def _load_path(path, members, connections):
    if not isinstance(path, list) or len(path) < 3 or len(path) % 2 == 0:
        raise PredictionError("INVALID_LOAD_PATH", 400)
    entities = []
    for index, item in enumerate(path):
        expected_kind = "CONNECTION" if index % 2 == 0 else "PHYSICAL_MEMBER"
        key_name = "connection_client_key" if expected_kind == "CONNECTION" else "physical_member_client_key"
        _only_keys(item, {"kind", key_name}, "INVALID_LOAD_PATH")
        if item.get("kind") != expected_kind:
            raise PredictionError("INVALID_LOAD_PATH", 400)
        key = item.get(key_name)
        lookup = connections if expected_kind == "CONNECTION" else members
        if not _string(key) or key not in lookup:
            raise PredictionError("INVALID_LOAD_PATH", 400)
        entities.append((expected_kind, key))
    if len(entities) != len(set(entities)):
        raise PredictionError("INVALID_LOAD_PATH", 400)
    for index in range(1, len(entities), 2):
        member = members[entities[index][1]]
        if not _is_incident(connections[entities[index - 1][1]], member):
            raise PredictionError("INVALID_LOAD_PATH", 400)
        if not _is_incident(connections[entities[index + 1][1]], member):
            raise PredictionError("INVALID_LOAD_PATH", 400)


def validate_prediction_payload(project, payload):
    """Validate only stored prediction-v1 shape and physical topology."""
    if not isinstance(payload, dict) or payload.get("schema_version") != "prediction-v1":
        _schema_error()
    _only_keys(
        payload,
        {
            "schema_version",
            "member_judgments",
            "max_displacement_location",
            "representative_load_path",
        },
        "PREDICTION_INVALID_SCHEMA",
    )
    _member_judgments(project, payload)
    members, connections = _topology(project)
    _physical_point(payload.get("max_displacement_location"), members, connections)
    _load_path(payload.get("representative_load_path"), members, connections)
    return payload
