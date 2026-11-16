# AV-01 Owner 视觉验收

Task 1–7 保留；本轮授权 Task 8–10。技术 QA 不代表产品验收。
M9/CAD 完整 Owner Acceptance：PENDING；Teacher Review：DEFERRED（不是 PASS）。不包含合并或发布授权。

本地完整报告、QA 原始日志/JUnit、三尺寸 A–K 截图与独立环境交接保存在：
`.superpowers/sdd/2026-10-27-av01-analysis-visualization/`。
该目录及私人运行目录不纳入 Git；密码仅在权限 0600 的私人凭证文件中。

## 最小 Owner Checklist

所有项目初始为 **PENDING**，仅由 Owner 填写。

| 项目 | 操作与观察 | Owner 状态 |
|---|---|---|
| 反力 | 在演示分析检查 Rx/Ry 的位置、正负方向、N 单位；同节点关联支座不重复分配反力 | PENDING |
| 荷载 | 检查每笔荷载与节点关联、箭头方向；显示分道的细引线仍指向原节点 | PENDING |
| 零与极小值 | 真零无方向箭头；极小非零值仍非零，原值可展开查看 | PENDING |
| 变形 | 开关变形层，比较原始浅灰虚线与主线；倍率说明清楚，没有安全判定暗示 | PENDING |
| 可用性 | 缺值与暂不可用提示不会假装为零；数值视图不依赖教学解释成功 | PENDING |
| 分段 | 中间节点保持折线段；MIXED 按各段事实查看，不显示平均构件轴力 | PENDING |
| 证据 | Hover 摘要、点击 Inspector 与键盘对象清单显示同一对象事实；完整原值按需展开 | PENDING |
| 生命周期 | 切换 A→B→A、离开 Results、Fit/Pan/Zoom 后不残留旧 Hover 或 Inspector | PENDING |
| 历史隔离 | 修改当前 Draft 后，历史图仍属于选定的 Saved Run | PENDING |
| 三种尺寸 | 1024×768、1280×800、1440×900：图、控制项、Inspector 和文字可读，无遮盖关键数值 | PENDING |
| 只读 | Results 无 CAD 编辑、Grip、变换右键；Manager/Developer/GRACE 只读，PURGED 拒绝访问 | PENDING |
| 教学与 CAD | Explanation/Reflection、保存与切 Run 正常；建模快捷键和保存行为不退步 | PENDING |

## 已知验收边界

B–G 受控矩阵用于可重复检查保存事实的显示，不冒充自然 Solver 输出。实际 Solver 三角桁架与历史/权限案例另有证据。
较密图形的标签可能移至侧边并使用较长引线；空间不足时保留明确提示和完整数值入口。
真实中文 IME/辅助技术实机体验不因 Browser 自动化而自动通过。
历史 memory-SQLite 截面 HTTP 500 风险维持原记录；file-SQLite 通过不代表修复。

下一步由 Owner 进行人工视觉验收并决定后续整合；本轮不 merge、push 或 deploy。

## 本轮技术证据（2026-11-14）

QA candidate：`254e08422bae8082f9a7bbb52b54df46241ae0eb`；产品行为代码为其祖先 `90c38f0`，之后仅同步既有 Browser 测试的 readonly Saved Run 契约。

- 单次完整 Browser：770 passed，0 failed / 0 skipped（含219项AV-01；99项M9命名模块、188项CAD命名模块均为子集，其他旧旅程/Workspace也包含在770内）。
- 单次完整 non-browser：983 passed /22 skipped；Mechanics131 passed为子集。22项并发测试仍未验证。
- Django check无问题、migration dry-run无变更；保存事实、源码指纹及受保护工作核对通过。
- 一位独立 reviewer 完整审查及同上下文最终差异补充核对：0 Critical；2 Important以真实RED→GREEN关闭（装饰支座引线不抢节点命中；可见反力箭头选择节点证据）；1项hidden/reopen测试强度建议明确deferred。
- 766 passed /4 failed的前次完整运行和所有中断/RED均保留，未合并计数冒充GREEN。四项旧测试按批准Spec§11改用可见SavedRun证据入口和明确载入条件，原M9/A-B/保存/Reflection/文案数值断言保留。

本机最终交付见 `.superpowers/sdd/2026-10-27-av01-analysis-visualization/` 中的 `AV01_FINALIZATION_REPORT.md`、`QA_INDEX.md`、`SCREENSHOT_GALLERY.md`、`OWNER_RUNTIME_HANDOFF.md`。运行环境须在QA后全新建立并通过公开UI smoke；密码和DB不纳入Git。

本节仅交付文档，不改变产品代码、测试、批准Spec/Plan、机械假设或人工Gate；所有Owner状态仍为PENDING。
