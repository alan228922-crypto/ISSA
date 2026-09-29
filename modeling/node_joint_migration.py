"""Audited, per-Project v1→v2 cutover; never a Django data migration."""

from dataclasses import dataclass
from math import isclose

from django.db import transaction

from analysis.hashing import model_hash
from idealization.truss2d import IdealizationError, idealize
from mechanics.truss2d.errors import MechanicsError
from mechanics.truss2d.solver import Truss2DSolver
from projects.models import Project
from projects.services import can_modify_project
from projects.workspace import _draft

from .models import DraftMigrationAudit
from .services import DraftSaveError, save_physical_draft
from .snapshot import build_physical_snapshot
from .topology import _parameter, find_unrepresented_passes


class MigrationBlocked(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class MigrationProposal:
    source_hash: str
    source_version: int
    draft_v2: dict
    node_mapping: dict[str, str]
    exceptions: set[tuple[str, str]]
    legacy_exceptions: dict


@dataclass(frozen=True)
class EquivalenceReport:
    equivalent: bool
    discrepancies: tuple[str, ...]


def _source(project):
    payload = _draft(project)
    if payload["schema_version"] != "physical-draft-v1":
        raise MigrationBlocked("NOT_LEGACY_PROJECT")
    return payload, model_hash(payload)


def build_migration_proposal(project):
    """Discover exactly the identity classes already present in v1 analysis."""
    old, source_hash = _source(project)
    old_nodes = {row["client_key"]: row for row in old["nodes"]}
    members = {row["client_key"]: row for row in old["physical_members"]}
    connections = {row["client_key"]: row for row in old["connections"]}
    support_refs = {row["target_connection_client_key"] for row in old["supports"] if row["target_connection_client_key"] is not None}
    load_refs = {row["target_connection_client_key"] for row in old["node_loads"] if row["target_connection_client_key"] is not None}
    node_mapping = {}
    new_nodes = {}
    incidence = set()
    endpoint_connection = {}
    represented_old_nodes = set()
    obsolete = []

    def add(key, old_node_key):
        if len(key) > 128 or old_node_key not in old_nodes:
            raise MigrationBlocked("UNMAPPABLE_NODE_IDENTITY")
        old_node = old_nodes[old_node_key]
        new_nodes[key] = {"client_key": key, "x_mm": old_node["x_mm"], "y_mm": old_node["y_mm"], "label": old_node.get("label", "")}
        represented_old_nodes.add(old_node_key)

    for connection_key, connection in sorted(connections.items()):
        location = connection["geometry_node_client_key"]
        participants = connection["participating_member_client_keys"]
        if location is None or any(member_key is None for member_key in participants):
            if location is None and not participants and connection_key not in support_refs | load_refs:
                obsolete.append(connection_key)
                continue
            raise MigrationBlocked("AMBIGUOUS_CONNECTION_PARTICIPATION")
        if not participants:
            if connection_key in support_refs | load_refs:
                raise MigrationBlocked("AMBIGUOUS_CONNECTION_PARTICIPATION")
            obsolete.append(connection_key)
            continue
        if location not in old_nodes:
            raise MigrationBlocked("MISSING_CONNECTION_NODE")
        joint_key = f"joint:{connection_key}"
        add(joint_key, location)
        node_mapping[f"connection:{connection_key}"] = joint_key
        point = (old_nodes[location]["x_mm"], old_nodes[location]["y_mm"])
        for member_key in participants:
            member = members.get(member_key)
            if member is None or member["start_node_client_key"] is None or member["end_node_client_key"] is None:
                raise MigrationBlocked("AMBIGUOUS_CONNECTION_PARTICIPATION")
            first = old_nodes[member["start_node_client_key"]]
            last = old_nodes[member["end_node_client_key"]]
            a = (first["x_mm"], first["y_mm"])
            b = (last["x_mm"], last["y_mm"])
            t = _parameter(point, a, b)
            if t is None:
                raise MigrationBlocked("CONNECTION_OFF_MEMBER")
            if t <= 1e-12 or t >= 1 - 1e-12:
                side = "START" if t <= 1e-12 else "END"
                identity = (member_key, side)
                if identity in endpoint_connection:
                    raise MigrationBlocked("DUPLICATE_ENDPOINT_CONNECTION")
                endpoint_connection[identity] = joint_key
            else:
                incidence.add((member_key, joint_key))

    new_members = []
    for member_key, member in sorted(members.items()):
        converted = {key: value for key, value in member.items() if key not in {"start_node_client_key", "end_node_client_key"}}
        for side, field in (("START", "start_node_client_key"), ("END", "end_node_client_key")):
            old_node_key = member[field]
            if old_node_key is None:
                converted[field] = None
                continue
            mapped = endpoint_connection.get((member_key, side))
            if mapped is None:
                mapped = f"free:{member_key}:{side}"
                add(mapped, old_node_key)
            node_mapping[f"free:{member_key}:{side}"] = mapped
            converted[field] = mapped
        new_members.append(converted)
    for old_key in sorted(set(old_nodes) - represented_old_nodes):
        add(f"geometry:{old_key}", old_key)

    coordinates = {key: (row["x_mm"], row["y_mm"]) for key, row in new_nodes.items()}
    same_pairs = []
    by_point = {}
    for key, point in sorted(coordinates.items()):
        for other in by_point.get(point, []):
            same_pairs.append([other, key, point[0], point[1]])
        by_point.setdefault(point, []).append(key)
    passes = find_unrepresented_passes(nodes=coordinates, members=new_members, incidences=incidence, exemptions=set())
    member_by_key = {row["client_key"]: row for row in new_members}
    pass_records = []
    for member_key, node_key in passes:
        member = member_by_key[member_key]
        x, y = coordinates[node_key]
        x1, y1 = coordinates[member["start_node_client_key"]]
        x2, y2 = coordinates[member["end_node_client_key"]]
        pass_records.append([member_key, node_key, x, y, x1, y1, x2, y2])
    draft = {
        "schema_version": "physical-draft-v2", "expected_draft_version": old["version"],
        "nodes": [new_nodes[key] for key in sorted(new_nodes)],
        "physical_members": new_members,
        "member_joint_incidences": [{"member_client_key": member_key, "node_client_key": node_key} for member_key, node_key in sorted(incidence)],
        "supports": [{
            "client_key": row["client_key"], "target_node_client_key": node_mapping.get(f"connection:{row['target_connection_client_key']}") if row["target_connection_client_key"] else None,
            "support_type": row["support_type"], "restrained_axis": row["restrained_axis"],
        } for row in old["supports"]],
        "node_loads": [{
            "client_key": row["client_key"], "target_node_client_key": node_mapping.get(f"connection:{row['target_connection_client_key']}") if row["target_connection_client_key"] else None,
            "fx_N": row["fx_N"], "fy_N": row["fy_N"], "label": row["label"],
        } for row in old["node_loads"]],
    }
    return MigrationProposal(source_hash, old["version"], draft, node_mapping, set(passes), {
        "same_coordinate_pairs": same_pairs,
        "nonparticipating_passes": pass_records,
        "obsolete_empty_connections": obsolete,
    })


def _close(left, right):
    return isclose(left, right, rel_tol=1e-8, abs_tol=1e-8)


def compare_legacy_v2(*, v1_snapshot, v2_snapshot, mapping):
    """Compare mapped graph, canonical properties, and Solver numerics."""
    try:
        old = idealize(v1_snapshot).model
        new = idealize(v2_snapshot).model
    except (IdealizationError, KeyError, ValueError) as exc:
        return EquivalenceReport(False, (f"IDEALIZATION:{exc}",))
    discrepancies = []
    old_nodes = {f"node:{mapping[row.id]}": row for row in old.nodes if row.id in mapping}
    new_nodes = {row.id: row for row in new.nodes}
    if len(old_nodes) != len(old.nodes) or old_nodes.keys() != new_nodes.keys():
        discrepancies.append("NODE_IDENTITIES")
    else:
        for key, row in old_nodes.items():
            target = new_nodes[key]
            if not _close(row.x_mm, target.x_mm) or not _close(row.y_mm, target.y_mm):
                discrepancies.append(f"NODE_POSITION:{key}")
    old_members = {row.id: row for row in old.members}
    new_members = {row.id: row for row in new.members}
    old_physical = {row["id"]: row for row in v1_snapshot["physical_members"]}
    new_physical = {row["id"]: row for row in v2_snapshot["physical_members"]}
    if old_physical.keys() != new_physical.keys():
        discrepancies.append("PHYSICAL_IDENTITIES")
    else:
        for key, row in old_physical.items():
            target = new_physical[key]
            for group, fields in (("material", ("E_MPa", "density_g_per_mm3")), ("section", ("A_mm2", "Ix_mm4", "Iy_mm4"))):
                for field in fields:
                    left, right = row[group].get(field), target[group].get(field)
                    if (left is None) != (right is None) or (left is not None and not _close(left, right)):
                        discrepancies.append(f"FROZEN_PROPERTY:{key}:{group}:{field}")
    if old_members.keys() != new_members.keys():
        discrepancies.append("MEMBER_SEGMENTS")
    else:
        for key, row in old_members.items():
            target = new_members[key]
            if (mapping.get(row.node_i), mapping.get(row.node_j)) != (target.node_i.removeprefix("node:"), target.node_j.removeprefix("node:")) or not _close(row.E_MPa, target.E_MPa) or not _close(row.A_mm2, target.A_mm2):
                discrepancies.append(f"MEMBER_DATA:{key}")
    old_supports = sorted((mapping.get(row.node_id), row.restrain_ux, row.restrain_uy) for row in old.supports)
    new_supports = sorted((row.node_id.removeprefix("node:"), row.restrain_ux, row.restrain_uy) for row in new.supports)
    if old_supports != new_supports:
        discrepancies.append("SUPPORTS")
    old_loads = sorted((mapping.get(row.node_id), row.fx_N, row.fy_N) for row in old.nodal_loads)
    new_loads = sorted((row.node_id.removeprefix("node:"), row.fx_N, row.fy_N) for row in new.nodal_loads)
    if len(old_loads) != len(new_loads) or any(a[0] != b[0] or not _close(a[1], b[1]) or not _close(a[2], b[2]) for a, b in zip(old_loads, new_loads)):
        discrepancies.append("LOADS")
    if discrepancies:
        return EquivalenceReport(False, tuple(discrepancies))
    try:
        old_result = Truss2DSolver().solve(old)
        new_result = Truss2DSolver().solve(new)
    except MechanicsError as exc:
        return EquivalenceReport(False, (f"LEGACY_SOLVER_INVALID:{exc.issues[0].code}",))
    for field, key_field, numeric_fields in (
        ("node_displacements", "node_id", ("ux_mm", "uy_mm")),
        ("support_reactions", "node_id", ("rx_N", "ry_N")),
        ("member_axial_forces", "member_id", ("axial_force_N",)),
    ):
        old_rows = {getattr(row, key_field): row for row in getattr(old_result, field)}
        new_rows = {getattr(row, key_field): row for row in getattr(new_result, field)}
        mapped = {f"node:{mapping[key]}" if key_field == "node_id" else key: row for key, row in old_rows.items()}
        if mapped.keys() != new_rows.keys():
            discrepancies.append(f"NUMERIC_KEYS:{field}")
            continue
        for key, row in mapped.items():
            if any(not _close(getattr(row, name), getattr(new_rows[key], name)) for name in numeric_fields):
                discrepancies.append(f"NUMERIC:{field}:{key}")
    from analysis.orchestration import _result

    try:
        old_post = _result(old, old_result, {key: key.rsplit(":", 1)[0] for key in old_members}, v1_snapshot)
        new_post = _result(new, new_result, {key: key.rsplit(":", 1)[0] for key in new_members}, v2_snapshot)
    except (TypeError, ValueError) as exc:
        return EquivalenceReport(False, (f"POSTPROCESS_INVALID:{exc}",))
    if not _close(old_post["total_mass_g"], new_post["total_mass_g"]):
        discrepancies.append("NUMERIC:TOTAL_MASS")
    old_rows = {row["analysis_member_id"]: row for row in old_post["member_results"]}
    new_rows = {row["analysis_member_id"]: row for row in new_post["member_results"]}
    for key in old_rows.keys() & new_rows.keys():
        for field in ("axial_force_N", "axial_stress_MPa", "mass_g"):
            left, right = old_rows[key][field], new_rows[key][field]
            if (left is None) != (right is None) or (left is not None and not _close(left, right)):
                discrepancies.append(f"NUMERIC:{field}:{key}")
    return EquivalenceReport(not discrepancies, tuple(discrepancies))


def convert_project(*, project_id, expected_draft_version, actor):
    """Commit v2 only after preflight, locked hash check, and equivalence."""
    preflight = Project.objects.get(pk=project_id)
    if not can_modify_project(actor, preflight):
        raise MigrationBlocked("PROJECT_WRITE_DENIED")
    _, preflight_hash = _source(preflight)
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        if project.draft_schema_version != "physical-draft-v1" or project.draft_version != expected_draft_version:
            raise MigrationBlocked("STALE_DRAFT")
        locked_payload, locked_hash = _source(project)
        if locked_hash != preflight_hash:
            raise MigrationBlocked("STALE_DRAFT")
        try:
            with transaction.atomic():
                proposal = build_migration_proposal(project)
                old_snapshot = build_physical_snapshot(project)
                audit = DraftMigrationAudit.objects.create(
                    project=project, status="CONVERTED", source_draft_version=project.draft_version,
                    source_hash=locked_hash, source_payload_json=locked_payload,
                    node_mapping_json=proposal.node_mapping, legacy_exceptions_json=proposal.legacy_exceptions,
                    target_draft_version=project.draft_version + 1,
                )
                project.draft_schema_version = "physical-draft-v2"
                project.save(update_fields=["draft_schema_version", "updated_at"])
                save_physical_draft(actor=actor, project=project, payload=proposal.draft_v2)
                project.refresh_from_db()
                new_snapshot = build_physical_snapshot(project)
                report = compare_legacy_v2(v1_snapshot=old_snapshot, v2_snapshot=new_snapshot, mapping=proposal.node_mapping)
                if not report.equivalent:
                    raise MigrationBlocked("EQUIVALENCE_MISMATCH:" + ",".join(report.discrepancies))
            return audit
        except (MigrationBlocked, DraftSaveError, ValueError) as exc:
            return DraftMigrationAudit.objects.create(
                project=project, status="BLOCKED", source_draft_version=project.draft_version,
                source_hash=locked_hash, source_payload_json=locked_payload,
                reason_code=(exc.code if isinstance(exc, (MigrationBlocked, DraftSaveError)) else "INCOMPLETE_LEGACY_DRAFT")[:100],
            )


def restore_v1_from_audit(*, project_id, expected_draft_version, actor):
    """Bounded recovery: refuse if a newer v2 edit would be overwritten."""
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        if not can_modify_project(actor, project):
            raise MigrationBlocked("PROJECT_WRITE_DENIED")
        audit = project.draft_migration_audits.filter(status="CONVERTED").order_by("-created_at", "-pk").first()
        if audit is None or project.draft_schema_version != "physical-draft-v2" or project.draft_version != expected_draft_version or project.draft_version != audit.target_draft_version:
            raise MigrationBlocked("NEWER_DRAFT_REQUIRES_OWNER_DISPOSITION")
        project.draft_schema_version = "physical-draft-v1"
        project.save(update_fields=["draft_schema_version", "updated_at"])
        payload = {**audit.source_payload_json, "expected_draft_version": project.draft_version}
        save_physical_draft(actor=actor, project=project, payload=payload)
        return DraftMigrationAudit.objects.create(
            project=project, status="RESTORED", source_draft_version=audit.source_draft_version,
            source_hash=audit.source_hash, source_payload_json=audit.source_payload_json,
            node_mapping_json=audit.node_mapping_json, legacy_exceptions_json=audit.legacy_exceptions_json,
            target_draft_version=project.draft_version + 1,
        )
