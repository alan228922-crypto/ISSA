from types import SimpleNamespace

import pytest


def physical_snapshot():
    return {
        "schema_version": "physical-snapshot-v1",
        "nodes": [
            {"id": "n1", "x_mm": 0.0, "y_mm": 0.0},
            {"id": "n_mid", "x_mm": 5.0, "y_mm": 0.0},
            {"id": "n2", "x_mm": 10.0, "y_mm": 0.0},
            {"id": "n3", "x_mm": 20.0, "y_mm": 0.0},
            {"id": "n4", "x_mm": 0.0, "y_mm": 10.0},
            {"id": "n5", "x_mm": 10.0, "y_mm": 10.0},
        ],
        "physical_members": [
            {"id": "m1", "start_node_id": "n1", "end_node_id": "n2", "material": {"E_MPa": 100.0}, "section": {"A_mm2": 2.0}},
            {"id": "m2", "start_node_id": "n2", "end_node_id": "n3", "material": {"E_MPa": 100.0}, "section": {"A_mm2": 2.0}},
            {"id": "m3", "start_node_id": "n4", "end_node_id": "n5", "material": {"E_MPa": 100.0}, "section": {"A_mm2": 2.0}},
        ],
        "connections": [
            {"id": "c1", "geometry_node_id": "n1", "participating_member_ids": ["m1"]},
            {"id": "c_mid", "geometry_node_id": "n_mid", "participating_member_ids": ["m1"]},
            {"id": "c2", "geometry_node_id": "n2", "participating_member_ids": ["m1", "m2"]},
            {"id": "c3", "geometry_node_id": "n3", "participating_member_ids": ["m2"]},
        ],
        "supports": [],
        "node_loads": [],
    }


def prediction_payload(*, m1_state="TENSION", m2_state="UNSURE", point=None):
    return {
        "schema_version": "prediction-v1",
        "member_judgments": [
            {"physical_member_client_key": "m1", "predicted_state": m1_state},
            {"physical_member_client_key": "m2", "predicted_state": m2_state},
            {"physical_member_client_key": "m3", "predicted_state": "UNSURE"},
        ],
        "max_displacement_location": point or {"kind": "CONNECTION", "connection_client_key": "c2"},
        "representative_load_path": [
            {"kind": "CONNECTION", "connection_client_key": "c1"},
            {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
            {"kind": "CONNECTION", "connection_client_key": "c2"},
            {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m2"},
            {"kind": "CONNECTION", "connection_client_key": "c3"},
        ],
    }


def authoritative_result(*, m1_first=10.0, m1_second=10.0, m2=-20.0, m3=5.0, displacements=None):
    return {
        "schema_version": "truss2d-result-v1",
        "member_results": [
            {"analysis_member_id": "m1:1", "physical_member_id": "m1", "axial_force_N": m1_first},
            {"analysis_member_id": "m1:2", "physical_member_id": "m1", "axial_force_N": m1_second},
            {"analysis_member_id": "m2:1", "physical_member_id": "m2", "axial_force_N": m2},
            {"analysis_member_id": "m3:1", "physical_member_id": "m3", "axial_force_N": m3},
        ],
        "node_displacements": displacements or [
            {"analysis_node_id": "connection:c1", "ux_mm": 0.0, "uy_mm": 0.0},
            {"analysis_node_id": "connection:c_mid", "ux_mm": 0.0, "uy_mm": 0.0},
            {"analysis_node_id": "connection:c2", "ux_mm": 3.0, "uy_mm": 4.0},
            {"analysis_node_id": "connection:c3", "ux_mm": 0.0, "uy_mm": 1.0},
            {"analysis_node_id": "free:m3:START", "ux_mm": 0.0, "uy_mm": 0.0},
            {"analysis_node_id": "free:m3:END", "ux_mm": 0.0, "uy_mm": 0.0},
        ],
    }


def run_for(*, payload=None, result=None, prediction_draft=7, revision_draft=7, prediction_project=1, run_project=1, model_hash="a" * 64):
    prediction = SimpleNamespace(
        id=2,
        project_id=prediction_project,
        source_draft_version=prediction_draft,
        status="COMPLETED",
        prediction_schema_version="prediction-v1",
        payload_json=payload or prediction_payload(),
    )
    revision = SimpleNamespace(
        source_draft_version=revision_draft,
        physical_snapshot_json=physical_snapshot(),
        model_hash=model_hash,
    )
    return SimpleNamespace(
        id=3,
        project_id=run_project,
        prediction=prediction,
        model_revision=revision,
        status="SUCCESS",
        result_schema_version="truss2d-result-v1",
        result_json=result or authoritative_result(),
    )


def compare(run):
    from learning.comparison import build_comparison

    return build_comparison(run=run)


def test_same_draft_is_accepted():
    assert compare(run_for())["comparison_available"] is True


def test_cross_draft_is_rejected():
    from learning.comparison import ComparisonError

    with pytest.raises(ComparisonError, match="COMPARE_SOURCE_MISMATCH"):
        compare(run_for(prediction_draft=7, revision_draft=8, model_hash="b" * 64))


def test_matching_hash_does_not_permit_cross_draft_comparison():
    from learning.comparison import ComparisonError

    with pytest.raises(ComparisonError, match="COMPARE_SOURCE_MISMATCH"):
        compare(run_for(prediction_draft=7, revision_draft=8, model_hash="a" * 64))


def test_cross_project_is_rejected():
    from learning.comparison import ComparisonError

    with pytest.raises(ComparisonError, match="COMPARE_PROJECT_MISMATCH"):
        compare(run_for(prediction_project=1, run_project=2))


@pytest.mark.parametrize(("force", "state"), [(10.0, "TENSION"), (-10.0, "COMPRESSION")])
def test_single_segment_teaching_state_is_derived(force, state):
    output = compare(run_for(result=authoritative_result(m2=force)))
    assert output["member_comparisons"][1]["actual"]["actual_state"] == state


def test_relative_threshold_classifies_small_segment_as_zero_force():
    output = compare(run_for(result=authoritative_result(m1_first=0.01, m1_second=20.0, m2=20.0)))
    assert output["member_comparisons"][0]["actual"]["segments"][0]["teaching_state"] == "ZERO_FORCE"


def test_absolute_floor_classifies_tiny_segment_as_zero_force():
    output = compare(run_for(result=authoritative_result(m1_first=0.0000005, m1_second=0.0000005, m2=0.0, m3=0.0)))
    assert output["member_comparisons"][0]["actual"]["actual_state"] == "ZERO_FORCE"


def test_all_zero_segments_use_absolute_floor_without_division():
    output = compare(run_for(result=authoritative_result(m1_first=0.0, m1_second=0.0, m2=0.0, m3=0.0)))
    assert {entry["actual"]["actual_state"] for entry in output["member_comparisons"]} == {"ZERO_FORCE"}


def test_same_state_segments_aggregate_to_physical_member_state():
    output = compare(run_for(result=authoritative_result(m1_first=-5.0, m1_second=-7.0)))
    assert output["member_comparisons"][0]["actual"]["actual_state"] == "COMPRESSION"


@pytest.mark.parametrize("second_force", [-10.0, 0.0])
def test_different_segment_states_aggregate_to_mixed(second_force):
    output = compare(run_for(result=authoritative_result(m1_first=10.0, m1_second=second_force)))
    assert output["member_comparisons"][0]["actual"]["actual_state"] == "MIXED"


def test_matching_prediction_is_match():
    output = compare(run_for(payload=prediction_payload(m1_state="TENSION")))
    assert output["member_comparisons"][0]["comparison_status"] == "MATCH"


def test_different_prediction_is_mismatch():
    output = compare(run_for(payload=prediction_payload(m1_state="COMPRESSION")))
    assert output["member_comparisons"][0]["comparison_status"] == "MISMATCH"


def test_unsure_prediction_remains_unsure():
    output = compare(run_for(payload=prediction_payload(m1_state="UNSURE")))
    assert output["member_comparisons"][0]["comparison_status"] == "UNSURE"


def test_mixed_actual_state_is_not_comparable_for_determinate_prediction():
    output = compare(run_for(result=authoritative_result(m1_first=10.0, m1_second=-10.0)))
    assert output["member_comparisons"][0]["comparison_status"] == "NOT_COMPARABLE"


def test_maximum_displacement_matches_predicted_connection_by_identity():
    maximum = compare(run_for())["maximum_displacement"]
    assert maximum["candidate_analysis_node_ids"] == ["connection:c2"]
    assert maximum["location_match"] is True


def test_maximum_displacement_non_match_is_false():
    output = compare(run_for(payload=prediction_payload(point={"kind": "CONNECTION", "connection_client_key": "c1"})))
    assert output["maximum_displacement"]["location_match"] is False


def test_tied_maximum_displacement_accepts_any_candidate():
    displacements = [
        {"analysis_node_id": "connection:c1", "ux_mm": 3.0, "uy_mm": 4.0},
        {"analysis_node_id": "connection:c_mid", "ux_mm": 4.0, "uy_mm": 3.0},
        {"analysis_node_id": "connection:c2", "ux_mm": 0.0, "uy_mm": 0.0},
        {"analysis_node_id": "connection:c3", "ux_mm": 0.0, "uy_mm": 0.0},
    ]
    output = compare(run_for(payload=prediction_payload(point={"kind": "CONNECTION", "connection_client_key": "c1"}), result=authoritative_result(displacements=displacements)))
    assert output["maximum_displacement"]["candidate_analysis_node_ids"] == ["connection:c1", "connection:c_mid"]
    assert output["maximum_displacement"]["location_match"] is True


def test_free_member_endpoint_mapping_uses_snapshot_identity_not_coordinates():
    displacements = [
        {"analysis_node_id": "connection:c1", "ux_mm": 0.0, "uy_mm": 0.0},
        {"analysis_node_id": "connection:c_mid", "ux_mm": 0.0, "uy_mm": 0.0},
        {"analysis_node_id": "connection:c2", "ux_mm": 0.0, "uy_mm": 0.0},
        {"analysis_node_id": "connection:c3", "ux_mm": 2.0, "uy_mm": 0.0},
        {"analysis_node_id": "free:m3:START", "ux_mm": 0.0, "uy_mm": 0.0},
        {"analysis_node_id": "free:m3:END", "ux_mm": 0.0, "uy_mm": 0.0},
    ]
    displacements[-1] = {"analysis_node_id": "free:m3:END", "ux_mm": 2.0, "uy_mm": 0.0}
    output = compare(run_for(payload=prediction_payload(point={"kind": "MEMBER_ENDPOINT", "physical_member_client_key": "m3", "endpoint": "END"}), result=authoritative_result(displacements=displacements)))
    assert output["maximum_displacement"]["location_match"] is True


def test_load_path_returns_single_segment_evidence_without_truth_scoring():
    output = compare(run_for())
    assert output["load_path_evidence"][1] == {
        "physical_member_client_key": "m2",
        "actual_state": "COMPRESSION",
        "segments": [{"analysis_member_id": "m2:1", "axial_force_N": -20.0, "teaching_state": "COMPRESSION"}],
    }
    assert not {"actual_load_path", "correct_path", "incorrect_path", "path_score"} & set(output)


def test_load_path_preserves_each_segment_for_a_split_physical_member():
    evidence = compare(run_for())["load_path_evidence"][0]
    assert evidence["actual_state"] == "TENSION"
    assert evidence["segments"] == [
        {"analysis_member_id": "m1:1", "axial_force_N": 10.0, "teaching_state": "TENSION"},
        {"analysis_member_id": "m1:2", "axial_force_N": 10.0, "teaching_state": "TENSION"},
    ]


def test_no_prediction_returns_the_limited_unavailable_contract():
    run = run_for()
    run.prediction = None
    assert compare(run) == {
        "schema_version": "comparison-v1",
        "comparison_available": False,
        "reason": "NO_PREDICTION",
        "project_id": 1,
        "analysis_run_id": 3,
    }


def test_comparison_v1_contains_only_the_minimum_facts():
    output = compare(run_for())
    assert set(output) == {
        "schema_version", "comparison_available", "reason", "project_id", "prediction_id",
        "analysis_run_id", "source_draft_version", "member_comparisons", "maximum_displacement",
        "load_path_evidence",
    }
    assert "physical_snapshot" not in output
    assert "result_json" not in output
