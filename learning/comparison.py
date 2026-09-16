"""Deterministic, non-persistent facts for the M4B comparison boundary."""

from math import hypot, isfinite

from idealization.truss2d import IdealizationError, idealize


class ComparisonError(ValueError):
    """A fail-closed comparison-contract violation."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _fail(code):
    raise ComparisonError(code)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _idealization(snapshot):
    try:
        return idealize(snapshot)
    except (AttributeError, IdealizationError, KeyError, TypeError, ZeroDivisionError) as exc:
        raise ComparisonError("COMPARE_SNAPSHOT_INVALID") from exc


def _segment_evidence(*, result, idealization):
    member_results = result.get("member_results")
    if not isinstance(member_results, list):
        _fail("COMPARE_RESULT_INVALID")
    expected_mapping = idealization.analysis_member_to_physical
    records = {}
    for entry in member_results:
        if not isinstance(entry, dict):
            _fail("COMPARE_RESULT_INVALID")
        segment_id = entry.get("analysis_member_id")
        physical_id = entry.get("physical_member_id")
        force = entry.get("axial_force_N")
        if (
            not isinstance(segment_id, str)
            or not isinstance(physical_id, str)
            or not _is_number(force)
            or segment_id in records
        ):
            _fail("COMPARE_RESULT_INVALID")
        records[segment_id] = (physical_id, force)
    if set(records) != set(expected_mapping):
        _fail("COMPARE_RESULT_PROVENANCE_MISMATCH")
    if any(records[segment_id][0] != expected_mapping[segment_id] for segment_id in records):
        _fail("COMPARE_RESULT_PROVENANCE_MISMATCH")

    threshold = max(1e-6, 0.001 * max(abs(force) for _, force in records.values()))
    projected = {}
    for segment_id in sorted(records):
        physical_id, force = records[segment_id]
        teaching_state = (
            "ZERO_FORCE" if abs(force) <= threshold
            else "TENSION" if force > threshold
            else "COMPRESSION"
        )
        projected.setdefault(physical_id, []).append({
            "analysis_member_id": segment_id,
            "axial_force_N": force,
            "teaching_state": teaching_state,
        })
    return {
        physical_id: {
            "actual_state": states[0]["teaching_state"] if len({item["teaching_state"] for item in states}) == 1 else "MIXED",
            "segments": states,
        }
        for physical_id, states in projected.items()
    }


def _prediction_node_id(*, point, idealization):
    if not isinstance(point, dict):
        _fail("COMPARE_POINT_UNMAPPABLE")
    if point.get("kind") == "CONNECTION" and isinstance(point.get("connection_client_key"), str):
        expected = {"kind": "connection", "id": f"connection:{point['connection_client_key']}"}
    elif (
        point.get("kind") == "MEMBER_ENDPOINT"
        and isinstance(point.get("physical_member_client_key"), str)
        and point.get("endpoint") in {"START", "END"}
    ):
        expected = {
            "kind": "free_endpoint",
            "id": f"free:{point['physical_member_client_key']}:{point['endpoint']}",
        }
    else:
        _fail("COMPARE_POINT_UNMAPPABLE")
    matches = [node_id for node_id, provenance in idealization.analysis_node_to_physical.items() if provenance == expected]
    if len(matches) != 1:
        _fail("COMPARE_POINT_UNMAPPABLE")
    return matches[0]


def _maximum_displacement(*, result, idealization, point):
    displacements = result.get("node_displacements")
    if not isinstance(displacements, list) or not displacements:
        _fail("COMPARE_RESULT_INVALID")
    magnitudes = {}
    for entry in displacements:
        if not isinstance(entry, dict):
            _fail("COMPARE_RESULT_INVALID")
        node_id, ux, uy = entry.get("analysis_node_id"), entry.get("ux_mm"), entry.get("uy_mm")
        if not isinstance(node_id, str) or not _is_number(ux) or not _is_number(uy) or node_id in magnitudes:
            _fail("COMPARE_RESULT_INVALID")
        magnitudes[node_id] = hypot(ux, uy)
    maximum = max(magnitudes.values())
    tolerance = max(1e-9, 1e-9 * maximum)
    candidates = sorted(node_id for node_id, magnitude in magnitudes.items() if maximum - magnitude <= tolerance)
    predicted_node = _prediction_node_id(point=point, idealization=idealization)
    if predicted_node not in magnitudes:
        _fail("COMPARE_POINT_UNMAPPABLE")
    return {
        "maximum_displacement_mm": maximum,
        "tie_tolerance_mm": tolerance,
        "predicted_point": point,
        "candidate_analysis_node_ids": candidates,
        "location_match": predicted_node in candidates,
    }


def _member_comparisons(*, payload, physical_evidence):
    judgments = payload.get("member_judgments")
    if not isinstance(judgments, list):
        _fail("COMPARE_PREDICTION_INVALID")
    comparisons = []
    seen = set()
    for judgment in sorted(judgments, key=lambda entry: entry.get("physical_member_client_key", "") if isinstance(entry, dict) else ""):
        if not isinstance(judgment, dict):
            _fail("COMPARE_PREDICTION_INVALID")
        physical_id = judgment.get("physical_member_client_key")
        predicted_state = judgment.get("predicted_state")
        if (
            not isinstance(physical_id, str)
            or physical_id in seen
            or physical_id not in physical_evidence
            or predicted_state not in {"TENSION", "COMPRESSION", "ZERO_FORCE", "UNSURE"}
        ):
            _fail("COMPARE_PREDICTION_INVALID")
        seen.add(physical_id)
        actual = physical_evidence[physical_id]
        if predicted_state == "UNSURE":
            comparison_status = "UNSURE"
        elif actual["actual_state"] == "MIXED":
            comparison_status = "NOT_COMPARABLE"
        elif predicted_state == actual["actual_state"]:
            comparison_status = "MATCH"
        else:
            comparison_status = "MISMATCH"
        comparisons.append({
            "physical_member_client_key": physical_id,
            "predicted_state": predicted_state,
            "actual": actual,
            "comparison_status": comparison_status,
        })
    return comparisons


def _load_path_evidence(*, payload, physical_evidence):
    path = payload.get("representative_load_path")
    if not isinstance(path, list):
        _fail("COMPARE_PREDICTION_INVALID")
    evidence = []
    for entry in path:
        if not isinstance(entry, dict) or entry.get("kind") != "PHYSICAL_MEMBER":
            continue
        physical_id = entry.get("physical_member_client_key")
        if not isinstance(physical_id, str) or physical_id not in physical_evidence:
            _fail("COMPARE_PREDICTION_INVALID")
        evidence.append({"physical_member_client_key": physical_id, **physical_evidence[physical_id]})
    return evidence


def build_comparison(*, run):
    """Return the minimum `comparison-v1` facts from immutable run evidence."""
    prediction = run.prediction
    if prediction is None:
        return {
            "schema_version": "comparison-v1",
            "comparison_available": False,
            "reason": "NO_PREDICTION",
            "project_id": run.project_id,
            "analysis_run_id": run.id,
        }
    if prediction.project_id != run.project_id:
        _fail("COMPARE_PROJECT_MISMATCH")
    revision = run.model_revision
    if prediction.source_draft_version != revision.source_draft_version:
        _fail("COMPARE_SOURCE_MISMATCH")
    if run.status != "SUCCESS" or run.result_schema_version != "truss2d-result-v1":
        _fail("COMPARE_RUN_NOT_SUCCESS")
    if prediction.status != "COMPLETED" or prediction.prediction_schema_version != "prediction-v1":
        _fail("COMPARE_PREDICTION_NOT_ELIGIBLE")
    result, payload = run.result_json, prediction.payload_json
    if not isinstance(result, dict) or result.get("schema_version") != "truss2d-result-v1" or not isinstance(payload, dict):
        _fail("COMPARE_RESULT_INVALID")

    idealization = _idealization(revision.physical_snapshot_json)
    physical_evidence = _segment_evidence(result=result, idealization=idealization)
    return {
        "schema_version": "comparison-v1",
        "comparison_available": True,
        "reason": None,
        "project_id": run.project_id,
        "prediction_id": prediction.id,
        "analysis_run_id": run.id,
        "source_draft_version": revision.source_draft_version,
        "member_comparisons": _member_comparisons(payload=payload, physical_evidence=physical_evidence),
        "maximum_displacement": _maximum_displacement(
            result=result,
            idealization=idealization,
            point=payload.get("max_displacement_location"),
        ),
        "load_path_evidence": _load_path_evidence(payload=payload, physical_evidence=physical_evidence),
    }
