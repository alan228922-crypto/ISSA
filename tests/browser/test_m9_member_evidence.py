"""Compare supplied member facts without reclassification, scoring or path truth."""

from copy import deepcopy

import pytest

from tests.browser.test_m9_explanation import context, m9_page, render_teaching, evidence_payload, capture_focused_evidence

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def compared_payload(*, state="TENSION", predicted="TENSION", status="MATCH", path=False):
    payload = evidence_payload()
    segments = [
        {"analysis_member_id": "opaque:1", "axial_force_N": 12.5 if state != "COMPRESSION" else -12.5,
         "teaching_state": "TENSION" if state == "MIXED" else state},
        {"analysis_member_id": "opaque:2", "axial_force_N": -400.25 if state in ("MIXED", "COMPRESSION") else 4.25,
         "teaching_state": "COMPRESSION" if state == "MIXED" else state},
    ]
    if state == "ZERO_FORCE":
        for segment in segments:
            segment["axial_force_N"] = 0.000001
    block = payload["explanation"]["blocks"][0]
    block["facts"] = {"actual_state": state, "segments": deepcopy(segments)}
    block["professional_values"]["segments"] = deepcopy(segments)
    item = payload["comparison"]["member_comparisons"][0]
    item.update(predicted_state=predicted, comparison_status=status,
                actual={"actual_state": state, "segments": deepcopy(segments)})
    if path:
        payload["comparison"]["load_path_evidence"] = [{
            "physical_member_client_key": "member-4", "actual_state": state, "segments": deepcopy(segments),
        }]
    return payload


@pytest.mark.parametrize(("state", "status", "word"), [
    ("TENSION", "MATCH", "和预测一致"), ("COMPRESSION", "MISMATCH", "和预测不同"),
])
def test_member_match_mismatch_wording_is_neutral(m9_page, state, status, word):
    observed = render_teaching(m9_page, compared_payload(state=state, status=status), renderer="renderComparison")
    assert word in observed["text"]
    assert "预测：受拉" in observed["text"]
    assert "分析：" in observed["text"] and "构件 M4" in observed["text"]
    assert all(word not in observed["text"] for word in ("正确", "错误", "score", "排名", "分数"))


def test_unsure_is_legal_non_scoring_prediction(m9_page):
    observed = render_teaching(m9_page, compared_payload(predicted="UNSURE", status="UNSURE"), renderer="renderComparison")
    assert "不确定" in observed["text"] and "分析：受拉" in observed["text"]
    assert all(word not in observed["text"] for word in ("和预测不同", "错误", "分数"))
    capture_focused_evidence(m9_page, 'unsure')


def test_mixed_retains_every_segment_fact(m9_page):
    payload = compared_payload(state="MIXED", status="NOT_COMPARABLE")
    original = deepcopy(payload)
    observed = render_teaching(m9_page, payload, renderer="renderComparison")
    assert "分析段 1" in observed["text"] and "分析段 2" in observed["text"]
    assert "12.5 N" in observed["text"] and "-400.25 N" in observed["text"]
    assert "受拉" in observed["text"] and "受压" in observed["text"]
    assert payload == original
    capture_focused_evidence(m9_page, 'mixed-all-segments')


def test_not_comparable_has_no_binary_verdict(m9_page):
    observed = render_teaching(m9_page, compared_payload(state="MIXED", status="NOT_COMPARABLE"), renderer="renderComparison")
    assert "单一" in observed["text"] and "分析段" in observed["text"]
    assert "和预测不同" not in observed["text"] and "和预测一致" not in observed["text"]


def test_student_path_is_hypothesis_not_solver_truth(m9_page):
    observed = render_teaching(m9_page, compared_payload(path=True), renderer="renderComparison")
    assert "学生传力假设" in observed["text"]
    assert "这些结果是否支持你的判断？" in observed["text"]
    assert "12.5 N" in observed["text"] and "4.25 N" in observed["text"]
    assert all(word not in observed["text"] for word in ("真实传力路径", "唯一路径", "路径正确", "路径错误"))


def test_zero_force_retains_approximation_caveat(m9_page):
    observed = render_teaching(m9_page, compared_payload(state="ZERO_FORCE", predicted="ZERO_FORCE"), renderer="renderComparison")
    assert "近似零力" in observed["text"] and "严格等于 0" in observed["text"]
    assert "0.000001 N" in observed["text"]


def test_conclusion_contains_supplied_neutral_comparison_summary(m9_page):
    observed = m9_page.evaluate("""async payload=>{
      const {buildTeachingView}=await import('/static/projects/workspace/teaching-view.js');
      const {showLevelOne,renderLevelOne}=await import('/static/projects/workspace/results.js');
      const view=buildTeachingView({payload,runNumber:1,workspace:{projectId:17,draftVersion:4,dirty:false}});
      const root=document.createElement('section');renderLevelOne(root,showLevelOne(view));return root.textContent;
    }""", compared_payload())
    assert "和预测一致 1 项" in observed
