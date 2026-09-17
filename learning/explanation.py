"""Deterministic zh-CN teaching blocks derived from authoritative analysis facts."""

from math import hypot

from .comparison import (
    ComparisonError,
    _idealization,
    _is_number,
    build_comparison,
    build_teaching_member_evidence,
)


# 閱讀提示：這個檔案把分析數值整理成學生看得懂的說明，不會重新計算結構力學。

# ============================================================
# 它接收已驗證的比較資料和 AnalysisRun，輸出 explanation-v1 的多個說明區塊。
# 每個區塊同時保留白話訊息與專業數值，讓學生先理解現象，再需要時查看細節。
# 如果結果來源、版本或對應關係不符合契約，這裡會停止產生說明，不猜測缺少的資料。
# ============================================================


class ExplanationError(ValueError):
    """A fail-closed explanation-contract violation."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _fail(code):
    raise ExplanationError(code)


def _copy_segments(segments):
    return [dict(segment) for segment in segments]


def _professional_segments(segments):
    return [
        {"analysis_member_id": segment["analysis_member_id"], "axial_force_N": segment["axial_force_N"]}
        for segment in segments
    ]


def _member_message(actual_state):
    templates = {
        "TENSION": (
            "该构件当前为受拉。",
            "该物理构件的分析段均显示为受拉。",
            "可结合各分析段的轴力数值进一步观察。",
        ),
        "COMPRESSION": (
            "该构件当前为受压。",
            "该物理构件的分析段均显示为受压。",
            "可结合各分析段的轴力数值进一步观察。",
        ),
        "ZERO_FORCE": (
            "该构件为近似零力构件。",
            "这是教学阈值下的近似零力，不表示轴力数学上严格等于 0。",
            "可结合各分析段的真实轴力数值进一步观察。",
        ),
        "MIXED": (
            "该构件的不同分析段呈现不同受力状态。",
            "理想化后的不同分析段不能被压成单一受拉或受压。",
            "可对照每个分析段的真实轴力和教学状态进一步观察。",
        ),
    }
    try:
        level_1, level_2, level_3 = templates[actual_state]
    except KeyError as exc:
        raise ExplanationError("EXPLANATION_FACTS_INVALID") from exc
    return {"level_1": level_1, "level_2": level_2, "level_3": level_3}


def _member_blocks(physical_evidence):
    # 先逐根物理構件整理受拉、受壓或混合狀態，再附上對應的軸力數值。
    blocks = []
    for physical_id in sorted(physical_evidence):
        evidence = physical_evidence[physical_id]
        segments = _copy_segments(evidence["segments"])
        blocks.append({
            "type": "MEMBER_FORCE_STATE",
            "subject": {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": physical_id},
            "facts": {"actual_state": evidence["actual_state"], "segments": segments},
            "message_zh_CN": _member_message(evidence["actual_state"]),
            "professional_values": {"segments": _professional_segments(segments)},
        })
    return blocks


def _maximum_displacement_block(*, run, comparison, idealization):
    # 從分析結果找出位移最大的節點，並在有預測時比較學生預測的位置是否相同。
    displacements = run.result_json.get("node_displacements")
    if not isinstance(displacements, list) or not displacements:
        _fail("EXPLANATION_RESULT_INVALID")
    by_node = {}
    for entry in displacements:
        if not isinstance(entry, dict):
            _fail("EXPLANATION_RESULT_INVALID")
        node_id, ux, uy = entry.get("analysis_node_id"), entry.get("ux_mm"), entry.get("uy_mm")
        if not isinstance(node_id, str) or not _is_number(ux) or not _is_number(uy) or node_id in by_node:
            _fail("EXPLANATION_RESULT_INVALID")
        if node_id not in idealization.analysis_node_to_physical:
            _fail("EXPLANATION_RESULT_PROVENANCE_MISMATCH")
        by_node[node_id] = {"analysis_node_id": node_id, "ux_mm": ux, "uy_mm": uy, "displacement_mm": hypot(ux, uy)}
    maximum = max(item["displacement_mm"] for item in by_node.values())
    tolerance = max(1e-9, 1e-9 * maximum)
    candidate_ids = sorted(node_id for node_id, item in by_node.items() if maximum - item["displacement_mm"] <= tolerance)
    candidate_values = [by_node[node_id] for node_id in candidate_ids]
    facts = {
        "maximum_displacement_mm": maximum,
        "tie_tolerance_mm": tolerance,
        "candidate_analysis_node_ids": candidate_ids,
    }
    level_2 = "可以观察该位置和相邻构件的变形关系。"
    if comparison is not None:
        compared = comparison.get("maximum_displacement")
        if not isinstance(compared, dict) or compared.get("candidate_analysis_node_ids") != candidate_ids:
            _fail("EXPLANATION_COMPARISON_INVALID")
        location_match = compared.get("location_match")
        if not isinstance(location_match, bool):
            _fail("EXPLANATION_COMPARISON_INVALID")
        facts["location_match"] = location_match
        level_2 = (
            "你的预测位置与最大位移位置一致；可以观察该位置和相邻构件的变形关系。"
            if location_match
            else "你的预测位置与最大位移位置不一致；可以观察该位置和相邻构件的变形关系。"
        )
    return {
        "type": "MAXIMUM_DISPLACEMENT",
        "subject": {"kind": "ANALYSIS_NODE_SET", "analysis_node_ids": candidate_ids},
        "facts": facts,
        "message_zh_CN": {
            "level_1": f"最大位移出现在 {'、'.join(candidate_ids)}，大小为 {maximum} mm。",
            "level_2": level_2,
            "level_3": "专业数值保留最大位移、候选节点的 ux、uy 和位移大小。",
        },
        "professional_values": {
            "maximum_displacement_mm": maximum,
            "tie_tolerance_mm": tolerance,
            "candidates": candidate_values,
        },
    }


def _comparison_message(status):
    templates = {
        "MATCH": (
            "你的预测与分析结果一致。",
            "可对照构件的受力状态理解原因。",
            "实际状态与各分析段的专业数值见下方。",
        ),
        "MISMATCH": (
            "你的预测与分析结果不同。",
            "可重新观察节点平衡和受力关系。",
            "实际状态与各分析段的专业数值见下方。",
        ),
        "UNSURE": (
            "你在分析前尚未确定该构件的受力状态。",
            "现在可依据分析结果观察。",
            "实际状态与各分析段的专业数值见下方。",
        ),
        "NOT_COMPARABLE": (
            "该构件的多个分析段呈现不同受力状态，不能用一个单一类别直接判断预测对错。",
            "请保留各分析段的证据进行观察，而不是把它改写为不一致。",
            "各分析段的专业数值见下方。",
        ),
    }
    try:
        level_1, level_2, level_3 = templates[status]
    except KeyError as exc:
        raise ExplanationError("EXPLANATION_COMPARISON_INVALID") from exc
    return {"level_1": level_1, "level_2": level_2, "level_3": level_3}


def _comparison_blocks(comparison):
    entries = comparison.get("member_comparisons")
    if not isinstance(entries, list):
        _fail("EXPLANATION_COMPARISON_INVALID")
    blocks = []
    for entry in sorted(entries, key=lambda item: item.get("physical_member_client_key", "") if isinstance(item, dict) else ""):
        if not isinstance(entry, dict) or not isinstance(entry.get("physical_member_client_key"), str):
            _fail("EXPLANATION_COMPARISON_INVALID")
        actual, status = entry.get("actual"), entry.get("comparison_status")
        if not isinstance(actual, dict) or not isinstance(actual.get("segments"), list):
            _fail("EXPLANATION_COMPARISON_INVALID")
        segments = _copy_segments(actual["segments"])
        blocks.append({
            "type": "PREDICTION_COMPARISON",
            "subject": {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": entry["physical_member_client_key"]},
            "facts": {
                "predicted_state": entry.get("predicted_state"),
                "actual_state": actual.get("actual_state"),
                "segments": segments,
                "comparison_status": status,
            },
            "message_zh_CN": _comparison_message(status),
            "professional_values": {"segments": _professional_segments(segments)},
        })
    return blocks


def _load_path_blocks(comparison):
    entries = comparison.get("load_path_evidence")
    if not isinstance(entries, list):
        _fail("EXPLANATION_COMPARISON_INVALID")
    blocks = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("physical_member_client_key"), str):
            _fail("EXPLANATION_COMPARISON_INVALID")
        segments = entry.get("segments")
        if not isinstance(segments, list):
            _fail("EXPLANATION_COMPARISON_INVALID")
        copied_segments = _copy_segments(segments)
        blocks.append({
            "type": "REPRESENTATIVE_LOAD_PATH",
            "subject": {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": entry["physical_member_client_key"]},
            "facts": {"actual_state": entry.get("actual_state"), "segments": copied_segments},
            "message_zh_CN": {
                "level_1": "这是你预测的一条重要传力路径中的构件。",
                "level_2": "可观察该构件及其分析段呈现的轴力证据。",
                "level_3": "各分析段的专业数值见下方。",
            },
            "professional_values": {"segments": _professional_segments(copied_segments)},
        })
    return blocks


def _comparison_for(*, run, comparison):
    if run.prediction is None:
        if comparison is not None:
            _fail("EXPLANATION_COMPARISON_INVALID")
        return None
    if comparison is None:
        try:
            comparison = build_comparison(run=run)
        except ComparisonError as exc:
            raise ExplanationError(exc.code) from exc
    if (
        not isinstance(comparison, dict)
        or comparison.get("schema_version") != "comparison-v1"
        or comparison.get("comparison_available") is not True
        or comparison.get("project_id") != run.project_id
        or comparison.get("analysis_run_id") != run.id
    ):
        _fail("EXPLANATION_COMPARISON_INVALID")
    return comparison


def build_explanation(*, run, comparison=None):
    # 依序建立構件受力、最大位移、預測比較和傳力路徑等教學區塊。
    """Return deterministic `explanation-v1` blocks without mechanics recomputation."""
    try:
        physical_evidence = build_teaching_member_evidence(run=run)
    except ComparisonError as exc:
        raise ExplanationError(exc.code) from exc
    try:
        idealization = _idealization(run.model_revision.physical_snapshot_json)
    except ComparisonError as exc:
        raise ExplanationError(exc.code) from exc
    compared = _comparison_for(run=run, comparison=comparison)
    blocks = _member_blocks(physical_evidence)
    blocks.append(_maximum_displacement_block(run=run, comparison=compared, idealization=idealization))
    if compared is not None:
        blocks.extend(_comparison_blocks(compared))
        blocks.extend(_load_path_blocks(compared))
    return {
        "schema_version": "explanation-v1",
        "explanation_available": True,
        "project_id": run.project_id,
        "analysis_run_id": run.id,
        "source_draft_version": run.model_revision.source_draft_version,
        "comparison_available": compared is not None,
        "comparison_reason": None if compared is not None else "NO_PREDICTION",
        "blocks": blocks,
    }
