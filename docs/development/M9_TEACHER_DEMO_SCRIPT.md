# M9 教师评审示范稿（约 8–12 分钟）

## 使用方式与材料边界

目标不是功能展示。请老师判断：大一至大二初学者能否从结果找到依据，自己解释，再提出下一次观察。

本次准备的是**既有证据包**，没有启动现场平台，也没有执行本轮现场演示。A 用真实公开分析画面；B、E 用既有真实公开操作记录讲解；C、D 用受控教学画面。需要真实点击才能判断时，记录 UNCERTAIN，不能宣称已现场验证。

讲者打开[教师简报](M9_TEACHER_REVIEW_BRIEF.md)与[空白评审表](M9_TEACHER_REVIEW_FORM.md)。截图只保存在本地 ignored evidence；移动资料包时须连同截图目录复制，不能只发 Markdown 后假定图片仍可打开。

## 10–12 分钟讲解顺序

| 时间 | 讲者操作／讲法 | 请老师观察 |
| --- | --- | --- |
| 0:00–1:00 | “不是教学生马上选最佳设计，而是让他知道自己在依据什么解释。”说明对象尚未学完力学。 | 五个核心问题是否适合作为最低活动。 |
| 1:00–3:00 | A：讲解学生先预测受拉／受压、最大位移位置与自己的传力假设。打开[预测对比](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/m9-1280-预测对比.png)。此图是分析后的对照，不冒充预测输入画面。顺带说明 B：可以不预测。 | “一致／不同”会不会像对错判分？[不确定示例](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/focused-unsure.png)是否合理？ |
| 3:00–5:00 | A：打开[结论](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/m9-1280-结论.png)。请老师指出一根受拉构件、一根受压构件及最大位移位置。说明这是已通过正常分析的记录，不在此重跑分析。 | 是否能先看懂发生了什么，而不先读大量数值。 |
| 5:00–7:00 | 打开[为什么](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/m9-1280-为什么.png)、[证据](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/m9-1280-evidence.png)、[展开的专业数据](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/m9-1280-level3.png)。用 E 解释“回看旧分析不能跟着新模型改变”。 | 能否指出构件、节点、分析段、数值？三层顺序及信息量如何？ |
| 7:00–8:00 | C、D：明确说“以下是受控教学案例，不是刚才三角形自然算出的结果”。展示[不同分析段](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/focused-mixed-all-segments.png)和[位移并列](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/focused-tied-candidates.png)。 | 不强迫单一受力状态，不强迫唯一最大位置。 |
| 8:00–10:00 | 打开[反思](../../.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/m9-1280-reflection.png)。说明文字是模拟操作者主动输入，不是平台生成。让老师判断三问能否让学生自己解释及提出下一次观察。 | 不代答、不评分、不告诉学生怎么改。 |
| 10:00–12:00 | 只问文末三个问题，记录原话及表单选择。若时间只有 8 分钟，缩短讲解，不删去证据来源说明；详细意见会后填写。 | 不把看完演示当作通过。 |

## 五个最小案例卡

### CASE A — Normal Prediction

**来源：PUBLIC REAL ANALYZE。** 同一真实公开操作流程：填写预测 → 正常分析 → 结论 → MATCH／MISMATCH → 三层说明 → 主动填写、保存并完成反思。均为 synthetic 数据，不是真实学生学习成效证明。

材料：上表六张 `m9-1280-*` 图。底杆为受拉、斜杆为受压；原预测选受拉，因此有一致与不同。请老师找依据，不问学生“答对几题”。截图是已有记录，本轮没有再次执行 Analyze。

### CASE B — No Prediction

**来源：既有 PUBLIC REAL ANALYZE 操作记录；无独立截图。** 实际已执行过：同样正常建模、保存、检查；跳过预测后分析，查看实际结果与说明，再主动填写并完成反思。对比面板说明没有预测，不产生虚构对照。

讲解句：“没有先猜，也能从实际结果开始学习；只是不能回头把结果当成自己的预测。”不拿 A 的有预测对照图假装 B。若老师需亲眼看无预测界面，记为待补展示，不勾选现场已操作。

### CASE C — MIXED member

**来源：CONTROLLED SUPPLIED-FACT CASE。** 使用 `focused-mixed-all-segments.png`。同一实际构件包含两个分析段：一个为受拉、轴力 12.5 N；另一个为受压、轴力 −400.25 N。

讲解句：“不能因为第二段数值绝对值较大，就说整根构件只有受压一种状态。”这是人为准备的已给定事实，用于检查教学表达，不是 A 三角形的真实求解结果；不新增安全或强度判断。

### CASE D — displacement ties

**来源：CONTROLLED SUPPLIED-FACT CASE。** 使用 `focused-tied-candidates.png`。给定最大位移为 0.5 mm，节点 N2、N3 都在候选集合中；两者同样合法，不指定第一名。

另有现存受控验证记录：最大值为 0 mm 时仍保留全部合法并列候选；缺漏数据则显示不可用，而不是补成 0。本包没有独立的 0 mm 图，**不能把 0.5 mm 图改称零值画面**。请老师判断零值并列是否需要另补教学说明或画面。

### CASE E — Historical Run

**来源：既有真实公开操作记录；无独立 A／B 对照截图。** 分析 A 后保存其反思；修改当前构件描述、荷载、材料，产生分析 B 及不同反思；再回看 A。A 的构件名称、数值、预测、反思仍属于 A，不使用 B 的新描述或数值。

讲解句：“旧分析像当时的实验记录。修改今天的模型，不应改写昨天的记录。”不向教师讲软件架构。A 的普通截图不是这次历史切换的截图，不混用两次记录。需要直观看到 A／B 切换时，记录待补展示。

## 最后只问这三个问题

A. 这样的顺序对刚学力学的学生是否容易理解？

B. 哪一层信息太多或太少？

C. 有没有任何一句话在力学上可能误导学生？

记录教师原话。涉及安全、屈曲、最佳设计、真实唯一传力路径、分类规则等新增力学判断，标记 **MECHANICS DECISION REQUIRED**，不现场修改。

## 讲者内部核对（无需向老师讲解）

实现来源固定为 `feat/results-teaching-loop-m9@3eeb50efcabf6ff8385313275f6562e005f59da2`。本轮只准备文档；不创建 runtime、DB、账号、假分析记录或新增截图。

现有证据定位：

- A、B：`tests/browser/test_m9_public_teaching_loop.py` 中正常预测与无预测两个真实公开旅程。
- C：`test_mixed_retains_every_segment_fact`；D：`test_ties_display_all_candidates_without_winner`、`test_zero_ties_and_missing_displacement_are_distinct`。
- E：`test_historical_run_a_survives_b_and_changed_draft`。
- 既有结果：见 [M9 实作证据](M9_IMPLEMENTATION_EVIDENCE.md)，本轮不重跑测试、不将旧结果称为新执行结果。

内部须保留的限制：R3 为反思已提交保存、切换分析时提示语过于肯定的 minor，不是跨分析写入缺陷；既有动态输入框可能遮挡画布点击，不属于 M9；曾出现 Analyze HTTP 500，**ROOT CAUSE NOT PROVEN**，后续完整回归通过，但不得称 fixed。

如改为真正现场操作，须使用本轮允许的全新独立临时 DB、唯一 `.localhost` 主机名及正常 cookie 设置，不能使用旧 DB；不修改代码、测试或 migration。没有真实运行，就不填写 URL／PID／账号或 smoke PASS。此脚本的准备不等于教师评审已完成。
