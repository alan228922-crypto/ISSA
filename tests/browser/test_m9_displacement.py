"""Location-only prediction against supplied maxima; no browser numerical solver."""

import pytest

from tests.browser.test_m9_explanation import context, m9_page, render_teaching, capture_focused_evidence
from tests.browser.test_m9_run_context import project_view, sample_payload

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def test_displacement_comparison_uses_server_candidates_and_match(m9_page):
    payload = sample_payload()
    payload["data"]["result_json"]["node_displacements"] = [
        {"analysis_node_id": "node:node-3", "ux_mm": 999.0, "uy_mm": 999.0},
    ]
    view = project_view(m9_page, payload)
    assert view["displacement"]["predictedLocationLabel"] == "节点 N2"
    assert view["displacement"]["locationMatch"] is True
    assert view["displacement"]["maximumMm"] == 0.5
    assert [row["label"] for row in view["displacement"]["candidates"]] == ["节点 N2", "节点 N3"]


def test_ties_display_all_candidates_without_winner(m9_page):
    observed = render_teaching(m9_page, sample_payload(), renderer="renderComparison")
    assert "预测位置：节点 N2" in observed["text"]
    assert "节点 N2" in observed["text"] and "节点 N3" in observed["text"]
    assert "0.5 mm" in observed["text"]
    assert m9_page.locator('[data-maximum-candidate]').count() == 2
    assert "唯一" not in observed["text"]
    capture_focused_evidence(m9_page, 'tied-candidates')


def test_zero_ties_and_missing_displacement_are_distinct(m9_page):
    payload = sample_payload()
    maximum = payload["explanation"]["blocks"][1]
    maximum["facts"]["maximum_displacement_mm"] = 0.0
    maximum["professional_values"]["maximum_displacement_mm"] = 0.0
    for candidate in maximum["professional_values"]["candidates"]:
        candidate.update(ux_mm=0.0, uy_mm=0.0, displacement_mm=0.0)
    payload["comparison"]["maximum_displacement"]["maximum_displacement_mm"] = 0.0
    view = project_view(m9_page, payload)
    assert view["displacement"]["available"] is True
    assert view["displacement"]["maximumMm"] == 0.0
    shown = render_teaching(m9_page, payload, renderer="renderComparison")
    assert "0 mm" in shown["text"]
    assert m9_page.locator('[data-maximum-candidate]').count() == 2
    del maximum["facts"]["maximum_displacement_mm"]
    assert project_view(m9_page, payload)["displacement"]["available"] is False
    missing = render_teaching(m9_page, payload, renderer="renderComparison")
    assert "位移" in missing["text"] and "暂不可用" in missing["text"]
    assert "0 mm" not in missing["text"]


def test_displacement_prediction_has_location_not_magnitude_or_percent(m9_page):
    shown = render_teaching(m9_page, sample_payload(), renderer="renderComparison")
    assert "预测位置" in shown["text"]
    assert "%" not in shown["text"] and "预测位移值" not in shown["text"]
    assert m9_page.locator('#m9-evidence-test input').count() == 0


@pytest.mark.parametrize("bad", ["unknown", "missing_values", "different_candidates", "different_magnitude"])
def test_invalid_candidate_provenance_is_unavailable_not_coordinate_matched(m9_page, bad):
    payload = sample_payload()
    maximum = payload["explanation"]["blocks"][1]
    if bad == "unknown":
        maximum["facts"]["candidate_analysis_node_ids"] = ["node:missing"]
    elif bad == "missing_values":
        maximum["professional_values"]["candidates"] = []
    elif bad == "different_candidates":
        payload["comparison"]["maximum_displacement"]["candidate_analysis_node_ids"] = ["node:node-3"]
    else:
        payload["comparison"]["maximum_displacement"]["maximum_displacement_mm"] = 0.6
    assert project_view(m9_page, payload)["displacement"]["available"] is False
    shown = render_teaching(m9_page, payload, renderer="renderComparison")
    assert "暂不可用" in shown["text"]
    assert "node:missing" not in shown["text"]


@pytest.mark.parametrize(("kind", "expected"), [("CONNECTION", "连接 C2"), ("MEMBER_ENDPOINT", "节点 N3")])
def test_legacy_location_uses_snapshot_provenance(m9_page, kind, expected):
    payload = sample_payload()
    geometry = payload["report"]["report"]["geometry_connectivity"]
    geometry.pop("member_joint_incidences")
    if kind == "CONNECTION":
        geometry["connections"] = [{"id": "connection-2", "geometry_node_id": "node-2", "participating_member_ids": ["member-4"]}]
        point = {"kind": kind, "connection_client_key": "connection-2"}
        identity = "connection:connection-2"
    else:
        geometry["connections"] = []
        point = {"kind": kind, "physical_member_client_key": "member-4", "endpoint": "END"}
        identity = "free:member-4:END"
    maximum = payload["explanation"]["blocks"][1]
    maximum["facts"]["candidate_analysis_node_ids"] = [identity]
    maximum["professional_values"]["candidates"] = [{"analysis_node_id": identity, "ux_mm": 0.3, "uy_mm": 0.4, "displacement_mm": 0.5}]
    payload["comparison"]["maximum_displacement"].update(predicted_point=point, candidate_analysis_node_ids=[identity])
    view = project_view(m9_page, payload)
    assert view["displacement"]["available"] is True
    assert view["displacement"]["predictedLocationLabel"] == expected


def test_no_prediction_preserves_actual_candidates_without_fake_match(m9_page):
    view = project_view(m9_page, sample_payload(comparison=False))
    assert view["displacement"]["available"] is True
    assert view["displacement"]["predictedLocationLabel"] is None
    assert view["displacement"]["locationMatch"] is None


def test_missing_result_fails_closed_without_zero_fallback(m9_page):
    payload = sample_payload()
    payload["data"]["result_json"] = None
    assert project_view(m9_page, payload)["available"] is False
