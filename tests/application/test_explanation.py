import json

import pytest

from tests.application.test_comparison import authoritative_result, prediction_payload, run_for


def explain(run, comparison=None):
    from learning.explanation import build_explanation

    return build_explanation(run=run, comparison=comparison)


def blocks(output, block_type):
    return [block for block in output["blocks"] if block["type"] == block_type]


def member_block(output, key="m1"):
    return next(block for block in blocks(output, "MEMBER_FORCE_STATE") if block["subject"]["physical_member_client_key"] == key)


def test_explain_succeeds_without_prediction_or_comparison():
    run = run_for()
    run.prediction = None

    output = explain(run)

    assert output["schema_version"] == "explanation-v1"
    assert output["comparison_available"] is False
    assert output["comparison_reason"] == "NO_PREDICTION"
    assert len(blocks(output, "MEMBER_FORCE_STATE")) == 3
    assert len(blocks(output, "MAXIMUM_DISPLACEMENT")) == 1
    assert not blocks(output, "PREDICTION_COMPARISON")
    assert not blocks(output, "REPRESENTATIVE_LOAD_PATH")


def test_tension_explanation_uses_the_authoritative_teaching_state():
    block = member_block(explain(run_for()))

    assert block["facts"]["actual_state"] == "TENSION"
    assert block["message_zh_CN"]["level_1"] == "该构件当前为受拉。"


def test_compression_explanation_uses_the_authoritative_teaching_state():
    output = explain(run_for(result=authoritative_result(m1_first=-10.0, m1_second=-5.0)))

    assert member_block(output)["message_zh_CN"]["level_1"] == "该构件当前为受压。"


def test_zero_force_calls_the_member_approximately_zero_force_and_keeps_real_force():
    output = explain(run_for(result=authoritative_result(m1_first=0.0000005, m1_second=0.0000005, m2=0.0, m3=0.0)))
    block = member_block(output)

    assert "近似零力构件" in block["message_zh_CN"]["level_1"]
    assert "不表示轴力数学上严格等于 0" in block["message_zh_CN"]["level_2"]
    assert block["professional_values"]["segments"][0]["axial_force_N"] == 0.0000005


def test_mixed_explanation_preserves_each_analysis_segment():
    output = explain(run_for(result=authoritative_result(m1_first=10.0, m1_second=-10.0)))
    block = member_block(output)

    assert block["facts"]["actual_state"] == "MIXED"
    assert [segment["teaching_state"] for segment in block["facts"]["segments"]] == ["TENSION", "COMPRESSION"]
    assert "不同分析段" in block["message_zh_CN"]["level_1"]


def comparison_block(output, key="m1"):
    return next(block for block in blocks(output, "PREDICTION_COMPARISON") if block["subject"]["physical_member_client_key"] == key)


def test_match_explanation_says_prediction_and_analysis_agree():
    assert "预测与分析结果一致" in comparison_block(explain(run_for()))["message_zh_CN"]["level_1"]


def test_mismatch_explanation_invites_force_relationship_observation():
    output = explain(run_for(payload=prediction_payload(m1_state="COMPRESSION")))
    message = comparison_block(output)["message_zh_CN"]

    assert "预测与分析结果不同" in message["level_1"]
    assert "节点平衡" in message["level_2"]


def test_unsure_explanation_remains_non_error():
    output = explain(run_for(payload=prediction_payload(m1_state="UNSURE")))
    message = comparison_block(output)["message_zh_CN"]

    assert "尚未确定" in message["level_1"]
    assert "答错" not in " ".join(message.values())


def test_not_comparable_explanation_remains_non_error():
    output = explain(run_for(result=authoritative_result(m1_first=10.0, m1_second=-10.0)))
    message = comparison_block(output)["message_zh_CN"]

    assert "不能用一个单一类别直接判断预测对错" in message["level_1"]
    assert "MISMATCH" not in json.dumps(message)


def test_maximum_displacement_block_explains_authoritative_maximum_location_and_value():
    block = blocks(explain(run_for()), "MAXIMUM_DISPLACEMENT")[0]

    assert block["facts"]["maximum_displacement_mm"] == 5.0
    assert block["facts"]["candidate_analysis_node_ids"] == ["connection:c2"]
    assert "最大位移" in block["message_zh_CN"]["level_1"]
    assert "connection:c2" in block["message_zh_CN"]["level_1"]
    assert "5.0 mm" in block["message_zh_CN"]["level_1"]


def test_maximum_displacement_explains_prediction_location_match():
    block = blocks(explain(run_for()), "MAXIMUM_DISPLACEMENT")[0]

    assert block["facts"]["location_match"] is True
    assert "一致" in block["message_zh_CN"]["level_2"]


def test_maximum_displacement_explains_prediction_location_non_match():
    output = explain(run_for(payload=prediction_payload(point={"kind": "CONNECTION", "connection_client_key": "c1"})))
    block = blocks(output, "MAXIMUM_DISPLACEMENT")[0]

    assert block["facts"]["location_match"] is False
    assert "不一致" in block["message_zh_CN"]["level_2"]


def test_maximum_displacement_rejects_node_outside_immutable_idealization_provenance():
    from learning.explanation import ExplanationError

    result = authoritative_result(displacements=[
        {"analysis_node_id": "unknown-node", "ux_mm": 3.0, "uy_mm": 4.0},
    ])
    run = run_for(result=result)
    run.prediction = None

    with pytest.raises(ExplanationError, match="EXPLANATION_RESULT_PROVENANCE_MISMATCH"):
        explain(run)


def test_representative_load_path_uses_prediction_wording_and_evidence():
    block = blocks(explain(run_for()), "REPRESENTATIVE_LOAD_PATH")[0]

    assert "你预测的一条重要传力路径" in block["message_zh_CN"]["level_1"]
    assert block["facts"]["actual_state"] == "TENSION"


def test_representative_load_path_preserves_multi_segment_evidence():
    block = blocks(explain(run_for()), "REPRESENTATIVE_LOAD_PATH")[0]

    assert [segment["analysis_member_id"] for segment in block["facts"]["segments"]] == ["m1:1", "m1:2"]


def test_explanation_has_only_structured_contract_blocks_and_no_design_recommendation():
    output = explain(run_for())

    assert set(output) == {
        "schema_version", "explanation_available", "project_id", "analysis_run_id",
        "source_draft_version", "comparison_available", "comparison_reason", "blocks",
    }
    assert all(set(block) == {"type", "subject", "facts", "message_zh_CN", "professional_values"} for block in output["blocks"])
    assert all(set(block["message_zh_CN"]) == {"level_1", "level_2", "level_3"} for block in output["blocks"])
    rendered = json.dumps(output, ensure_ascii=False)
    messages = " ".join(message for block in output["blocks"] for message in block["message_zh_CN"].values())
    assert "PhysicalMember" not in messages
    for forbidden in ("必须删除", "必须加强", "设计很好", "设计很差", "一定会失效", "最佳设计", "actual_load_path", "correct_path", "incorrect_path", "path_score"):
        assert forbidden not in rendered
