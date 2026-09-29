import copy

import pytest

from idealization.truss2d import IdealizationError, idealize


def snapshot():
    return {
        "schema_version": "physical-snapshot-v2", "analysis_type": "TRUSS_2D",
        "units": {"length": "mm", "force": "N", "stress": "MPa", "mass": "g"},
        "nodes": [
            {"id": "a", "x_mm": 0.0, "y_mm": 0.0},
            {"id": "b", "x_mm": 1000.0, "y_mm": 0.0},
            {"id": "mid", "x_mm": 500.0, "y_mm": 0.0},
        ],
        "physical_members": [{
            "id": "m", "start_node_id": "a", "end_node_id": "b", "is_active": True,
            "material": {"E_MPa": 200000.0, "density_g_per_mm3": 0.00785},
            "section": {"A_mm2": 100.0},
        }],
        "member_joint_incidences": [{"member_id": "m", "node_id": "mid"}],
        "supports": [{"id": "s", "node_id": "a", "support_type": "PINNED", "restrained_axis": None}],
        "node_loads": [{"id": "l", "node_id": "b", "fx_N": 5.0, "fy_N": -20.0}],
    }


def test_one_physical_member_splits_without_identity_loss():
    result = idealize(snapshot())
    assert [member.id for member in result.model.members] == ["m:1", "m:2"]
    assert result.physical_member_to_analysis["m"] == ["m:1", "m:2"]
    assert result.model.schema_version == "truss2d-input-v1"
    assert result.analysis_node_to_physical["node:mid"] == {"kind": "node", "id": "mid"}


def test_direct_node_support_load_and_units():
    result = idealize(snapshot()).model
    assert result.members[0].E_MPa == 200000.0
    assert result.members[0].A_mm2 == 100.0
    assert (result.supports[0].node_id, result.supports[0].restrain_ux, result.supports[0].restrain_uy) == ("node:a", True, True)
    assert (result.nodal_loads[0].node_id, result.nodal_loads[0].fx_N, result.nodal_loads[0].fy_N) == ("node:b", 5.0, -20.0)


def test_v2_idealizer_does_not_infer_from_overlapping_coordinates():
    draft = snapshot()
    draft["nodes"].append({"id": "other", "x_mm": 500.0, "y_mm": 0.0})
    result = idealize(draft)
    assert "node:other" not in {node.id for node in result.model.nodes}


def test_crossing_without_node_has_no_shared_dof():
    draft = snapshot()
    draft["nodes"].extend([{"id": "c", "x_mm": 500.0, "y_mm": -500.0}, {"id": "d", "x_mm": 500.0, "y_mm": 500.0}])
    draft["physical_members"].append({**copy.deepcopy(draft["physical_members"][0]), "id": "vertical", "start_node_id": "c", "end_node_id": "d"})
    result = idealize(draft)
    assert result.physical_member_to_analysis["vertical"] == ["vertical:1"]
    assert "node:mid" not in {node_id for member in result.model.members if member.id == "vertical:1" for node_id in (member.node_i, member.node_j)}


def test_endpoint_joint_and_three_member_interior_joint_are_explicit():
    draft = snapshot()
    draft["nodes"].extend([{"id": "c", "x_mm": 500.0, "y_mm": -500.0}, {"id": "d", "x_mm": 500.0, "y_mm": 500.0}, {"id": "e", "x_mm": 1000.0, "y_mm": 500.0}])
    base = draft["physical_members"][0]
    draft["physical_members"].extend([
        {**copy.deepcopy(base), "id": "vertical", "start_node_id": "c", "end_node_id": "d"},
        {**copy.deepcopy(base), "id": "diagonal", "start_node_id": "mid", "end_node_id": "e"},
    ])
    draft["member_joint_incidences"].append({"member_id": "vertical", "node_id": "mid"})
    result = idealize(draft)
    assert len(result.physical_member_to_analysis["vertical"]) == 2
    assert next(m for m in result.model.members if m.id == "diagonal:1").node_i == "node:mid"
    assert len([m for m in result.model.members if "node:mid" in (m.node_i, m.node_j)]) == 5


def test_invalid_explicit_incidence_is_not_repaired():
    draft = snapshot()
    draft["nodes"][2]["y_mm"] = 1.0
    with pytest.raises(IdealizationError):
        idealize(draft)
