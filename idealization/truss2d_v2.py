"""Explicit Node-as-Joint idealization; no coordinate-based graph inference."""

from mechanics.truss2d.model import Member, Node, NodalLoad, Support, TrussModel
from modeling.topology import ordered_member_nodes

from .truss2d import IdealizationError, IdealizationResult


def idealize_v2(snapshot):
    if snapshot.get("schema_version") != "physical-snapshot-v2":
        raise IdealizationError("UNSUPPORTED_SNAPSHOT_SCHEMA")
    nodes = {row["id"]: row for row in snapshot["nodes"]}
    coordinates = {key: (row["x_mm"], row["y_mm"]) for key, row in nodes.items()}
    incidence = {(row["member_id"], row["node_id"]) for row in snapshot["member_joint_incidences"]}
    if len(incidence) != len(snapshot["member_joint_incidences"]):
        raise IdealizationError("DUPLICATE_MEMBER_INCIDENCE")
    output_nodes = {}
    output_members = []
    node_map = {}
    member_map = {}
    reverse = {}
    used_incidence = set()
    for row in sorted(snapshot["physical_members"], key=lambda member: member["id"]):
        member = {"client_key": row["id"], "start_node_client_key": row["start_node_id"], "end_node_client_key": row["end_node_id"]}
        try:
            path = ordered_member_nodes(member, coordinates, incidence)
        except (KeyError, ValueError) as exc:
            raise IdealizationError(str(exc)) from exc
        used_incidence.update((row["id"], key) for key in path[1:-1])
        for key in path:
            analysis_key = f"node:{key}"
            if analysis_key not in output_nodes:
                x, y = coordinates[key]
                output_nodes[analysis_key] = Node(analysis_key, x, y)
                node_map[analysis_key] = {"kind": "node", "id": key}
        segment_ids = []
        for position, (first, last) in enumerate(zip(path, path[1:]), start=1):
            analysis_id = f"{row['id']}:{position}"
            output_members.append(Member(analysis_id, f"node:{first}", f"node:{last}", row["material"]["E_MPa"], row["section"]["A_mm2"]))
            member_map[analysis_id] = row["id"]
            segment_ids.append(analysis_id)
        reverse[row["id"]] = segment_ids
    if used_incidence != incidence:
        raise IdealizationError("INVALID_MEMBER_INCIDENCE")
    supports = []
    for row in snapshot["supports"]:
        key = f"node:{row['node_id']}"
        if key not in output_nodes:
            raise IdealizationError("UNATTACHED_SUPPORT_NODE")
        supports.append(Support(key, row["support_type"] == "PINNED" or row["restrained_axis"] == "X", row["support_type"] == "PINNED" or row["restrained_axis"] == "Y"))
    loads = []
    for row in snapshot["node_loads"]:
        key = f"node:{row['node_id']}"
        if key not in output_nodes:
            raise IdealizationError("UNATTACHED_LOAD_NODE")
        loads.append(NodalLoad(key, row["fx_N"], row["fy_N"]))
    return IdealizationResult(
        TrussModel("truss2d-input-v1", tuple(output_nodes.values()), tuple(output_members), tuple(supports), tuple(loads)),
        node_map, member_map, reverse,
    )
