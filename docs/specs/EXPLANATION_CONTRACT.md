# Explanation Contract — M4B

## 状态与范围

- 状态：**CONFIRMED — M4B Gate 2A contract freeze**
- 父级权威：`MASTER_SPEC.md v1.7`
- Schema：`explanation-v1`
- 范围：由成功 AnalysisRun 的冻结权威事实、不可变 ModelRevision provenance，以及可选 `comparison-v1` 派生的确定性初学者教学说明。

Explain 不是 Solver，不调用 Solver，不重新计算位移、反力、轴力、应力、质量或结构正确性，也不得修改任何数值结果。它只将已有权威事实投影为可理解的简体中文说明；这一投影不构成结构评价、设计决策或安全判断。

P0 Explain Core 只使用确定性模板和规则。它不调用 AI/LLM，不引入通用 CMS 或 i18n 框架；未来的语言辅助也只能消费该权威输出，不能改变工程结论。

## 输入与 Soft Gate

Explain 的基础输入是 `SUCCESS` AnalysisRun、其 `truss2d-result-v1` 结果和 linked immutable ModelRevision snapshot。它使用与 `COMPARISON_CONTRACT.md` 相同的确定性 teaching-member evidence projection：O-007 阈值先作用于全部 analysis segments，再将 segment evidence 投影为 PhysicalMember `actual_state` 和完整 segments。这个投影不求解或改写 mechanics；它只消费既有 authoritative forces 与冻结 idealization provenance，且实现时必须复用同一纯规则，不能复制出不同阈值语义。

`comparison-v1` 是可选输入：

- 有 completed Prediction 且可比较时，Explain 可消费 member comparison、maximum displacement 和 representative load-path evidence。
- `AnalysisRun.prediction = null` 时，Explain 仍返回 member-force 和 maximum-displacement blocks；`comparison_available` 为 `false`，`comparison_reason` 为 `NO_PREDICTION`，并省略 prediction-comparison / load-path blocks。
- `NO_PREDICTION` 是合法产品流，不是 Explain error，也不阻止 Analyze 或 Explain。

Explain 必须 fail closed 于非成功 Run、未知 result schema 或不一致的 immutable provenance；这些是 contract failure，不得使用 mutable Project draft、坐标接近猜测或 ORM primary key 回退。

## `explanation-v1` 输出

输出是稳定顺序的结构化 blocks，不是不可测试的自由长文：

```json
{
  "schema_version": "explanation-v1",
  "explanation_available": true,
  "project_id": 1,
  "analysis_run_id": 3,
  "source_draft_version": 7,
  "comparison_available": true,
  "comparison_reason": null,
  "blocks": [
    {
      "type": "MEMBER_FORCE_STATE",
      "subject": {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
      "facts": {
        "actual_state": "TENSION",
        "segments": [
          {"analysis_member_id": "m1:1", "axial_force_N": 12.5, "teaching_state": "TENSION"}
        ]
      },
      "message_zh_CN": {
        "level_1": "该构件当前为受拉。",
        "level_2": "分析段的受力状态均显示为受拉。",
        "level_3": "可结合各分析段的轴力数值进一步观察。"
      },
      "professional_values": {"segments": [{"analysis_member_id": "m1:1", "axial_force_N": 12.5}]}
    }
  ]
}
```

`type`、`subject`、`facts` 和三层 `message_zh_CN` 是每个 block 的最低结构。所有用户可见 message 必须为 zh-CN；`professional_values` 只放支持说明的真实数值/标识，不得复制完整 snapshot、solver input 或 result payload。

固定 block 排序如下：

1. `MEMBER_FORCE_STATE`，按 `physical_member_client_key`；
2. `MAXIMUM_DISPLACEMENT`；
3. 有 comparison 时的 `PREDICTION_COMPARISON`，按 `physical_member_client_key`；
4. 有 comparison load-path evidence 时的 `REPRESENTATIVE_LOAD_PATH`，保持 Prediction path 的成员顺序。

同一输入必须产生相同 blocks、事实、排序和模板文字。数值格式化只可改变展示精度，不得改变 facts 中的 authoritative numeric value。

## Member force-state templates

`MEMBER_FORCE_STATE.facts` 必须保留 PhysicalMember `actual_state` 和所有 segment 的稳定 `analysis_member_id`、真实 `axial_force_N`、`teaching_state`。模板语义固定如下：

| `actual_state` | Level 1 | Level 2 必须表达 | Level 3 |
| --- | --- | --- | --- |
| `TENSION` | “该构件当前为受拉。” | 该 PhysicalMember 的 analysis segments 均为受拉。 | 各 segment 的真实轴力 N。 |
| `COMPRESSION` | “该构件当前为受压。” | 该 PhysicalMember 的 analysis segments 均为受压。 | 各 segment 的真实轴力 N。 |
| `ZERO_FORCE` | “该构件为近似零力构件。” | 这是教学阈值下的近似零力，不表示轴力数学上严格等于 0。 | 各 segment 的真实轴力 N。 |
| `MIXED` | “该构件的不同分析段呈现不同受力状态。” | 显式说明理想化后的不同 segments 不能被压成单一受拉或受压。 | 每个 segment 的真实轴力 N 与 teaching state。 |

Explain 不得把 `MIXED` 简化为任一单一状态，也不得以最大绝对轴力 segment 代表 PhysicalMember。

## Prediction-comparison templates

`PREDICTION_COMPARISON` 只在 `comparison-v1` 可用时出现，复用其 `comparison_status`、predicted state、actual state 与 segment evidence：

| `comparison_status` | Level 1 | Level 2 必须表达 |
| --- | --- |
| `MATCH` | “你的预测与分析结果一致。” | 可对照构件的受力状态理解原因。 |
| `MISMATCH` | “你的预测与分析结果不同。” | 可重新观察节点平衡和受力关系。 |
| `UNSURE` | “你在分析前尚未确定该构件的受力状态。” | 现在可依据分析结果观察。 |
| `NOT_COMPARABLE` | “该构件的多个分析段呈现不同受力状态，不能用一个单一类别直接判断预测对错。” | 保留各 segment evidence，且不得改写为 `MISMATCH`。 |

这些 blocks 不得出现“错误”“答错”“失分”、分数、百分比、等级、排名或通过/不通过语义。

## Maximum-displacement templates

`MAXIMUM_DISPLACEMENT` 从 authoritative node displacement facts 按 `COMPARISON_CONTRACT.md` 的固定 magnitude 与 tie policy 派生。它必须报告真实 maximum magnitude 和所有 maximum candidate 的稳定 analysis-node identity/provenance；不得用坐标猜测位置。

- Level 1：说明“最大位移出现在 [候选位置]，大小为 [magnitude] mm。”
- Level 2：只引导学生观察该位置和相邻构件的变形关系。
- Level 3：保留真实 `ux_mm`、`uy_mm`、magnitude 和 tie candidates。
- 有 comparison 时，可额外说明 Prediction location 是否命中 candidate set；没有 Prediction 时不生成比较判断。

不得据此评价结构优劣、安全性、是否失效，或自动建议加固/修改设计。

## Representative-load-path templates

`REPRESENTATIVE_LOAD_PATH` 只在 `comparison-v1.load_path_evidence` 存在时出现。它只能复用 Prediction 的 representative path 和其中每个 PhysicalMember 的 `actual_state`、完整 segment evidence。

- Level 1 必须称为“你预测的一条重要传力路径”。
- Level 2 说明路径上构件/segments 呈现的轴力证据，供学生观察。
- Level 3 保留各 segment 的 `analysis_member_id`、真实 `axial_force_N` 与 teaching state。

它不得生成 `actual_load_path`、`correct_path`、`incorrect_path`、唯一“真实传力路径”、path score 或正确性判断。

## Explicit exclusions

`explanation-v1` 不包含 Reflection、Design Rationale、自动优化、设计推荐、Euler final risk explanation、Frame explanation、HTTP、UI、AI generation、ORM Explanation/ExplanationBlock/TeachingMessage model 或任何 persistence。Explain 只帮助理解，不替学生完成设计决策。

## HTTP disclosure boundary

M4B Explain 的 HTTP boundary 是 `GET /projects/<project_id>/analyses/<run_id>/explanation/`，其完整规则见 `API_AND_APPLICATION_FLOW.md`。它沿用 M3 `ok` success envelope，唯一 domain payload 为嵌套的 `explanation-v1`。它同样是 result disclosure boundary：Student owner 在任何 authoritative explanation blocks 返回前，必须经既有 StudentResultReveal service 完成 reveal persistence；Manager/Developer 的合法 read 不创建 student reveal。无 Prediction 仍返回完整的无比较 Explain，并使用 `comparison_reason: "NO_PREDICTION"`，不是 error。

## Gate 2A self-review

- 无 Prediction 时 Explain 仍可用，`NO_PREDICTION` 不成为错误。
- Explain 不重新计算 mechanics，不改动数值结果。
- `ZERO_FORCE` 使用“近似零力构件”；`MIXED` 保留 segment differences。
- `UNSURE` 和 `NOT_COMPARABLE` 都不是错误或失分判断。
- Load path 是学生预测的一条重要路径，不是 Solver truth。
- 没有结构评分、自动设计建议、AI dependency 或 persistence。
