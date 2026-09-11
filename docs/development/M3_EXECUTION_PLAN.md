# M3 执行计划

依据 MASTER_SPEC v1.3 与 CODEX_IMPLEMENTATION_PLAN 执行；本记录不取代 Source of Truth。

1. Task 8/9：建立最小 Project、Section 与 physical-draft-v1 全量保存；以 server-side ownership、optimistic concurrency、原子替换与 Support restrained_axis contract 为测试 gate。
2. Task 10：创建不可变 physical-snapshot-v1、ModelRevision 与 canonical SHA-256 hash；验证 draft/material/section 后续修改不会改变既有 revision。
3. Task 16：将显式 Connection 转为 TrussModel，保持未连接的同坐标端点独立；支持中间 Connection 拆分与稳定 mapping。
4. Task 17：创建 SolverVersion、AnalysisRun 和 revision reuse；M1 solver 保持不变。
5. Task 18/19：实现 Model Check 的简体中文解释映射，以及 save/check/analyze/result 的最小 server-side JSON endpoints。

约束：不进入 M4；不实现 Frame、任意角度支座、Self Weight、自动 Euler K、Project dashboard 或完整 UI；O-001、O-003、O-004、O-005 保持开放。
