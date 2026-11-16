# ISSA Workspace / CAD UI Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将批准Design v1.1接入W01–W08真实Workspace，保留CAD与分析前流程的全部数据/键盘/API契约。

**Architecture:** 沿用Django模板、Renderer及原事件绑定。提取Phase2A控制元件为共用CSS，用同一token；新增Workspace呈现样式仅作用于build/check/prediction/analyze。移动真实DOM控件，不复制控件，不替换事件/data hook。Results/AV01主体与总结保持原实现。

**Tech Stack:** Django Templates、Vanilla JS、CSS、SVG、pytest/Playwright；不新增依赖/CDN。

**Spec:** 设计commit7933932…的design/issa-product-uiux-v1/{ISSA_UI_INVENTORY,ISSA_DESIGN_SYSTEM,ISSA_UI_REDESIGN_SPEC,ENGINEERING_GRAPHICS_SYSTEM,ISSA_ICON_INVENTORY,UI_IMPLEMENTATION_HANDOFF}.md；本轮Owner指令；来源1cc0334…。不修改批准Spec/Plan。

## Global Constraints

- 只处理W01–W08；不改Solver/Mechanics/Schema/权限/AnalysisRun、批准Spec、CAD命令/快捷键/IME/焦点优先级/世界坐标/Snap/ORTHO/状态机。
- 保留全部既有HTML id/data hook、表单关系和真实工程值。图形由原模型/Renderer生成，不导入设计fixture。
- 不操作原CAD五项未提交修改、Owner50442、Phase2A50584或其他worktree/DB。新分支feat/issa-ui-phase2b1。
- 用户已明确要求直接实施批准设计；不重复设计批准流程。inline执行，最后fresh reviewer；不merge/push/deploy。

## Review Focus

- 1024/1280/1440×768/800/900：Canvas与状态栏不互盖，两侧面板独立滚动；短视口允许整页滚动。
- 工具/编辑命令移动后，querySelector仍唯一；新SVG不能吞掉按钮事件或改变label。
- 动态输入保留64px专用区域，不覆盖或推移Canvas交互途中坐标；IME/Tab/Esc/右键/native dialog仍交回原处理器。
- 保存/dirty/busy/版本冲突与必要错误不能被新布局隐藏；保留全部状态来源，一处主要保存状态。
- CSS不改变Results/AV01/summary主体；提取共享control样式不能破坏SSR。

### Task 1: 共用元件与Build/CAD布局（W01–W05）
**Files:** templates/projects/workspace.html；新增projects/static/ui/controls.css与projects/static/projects/workspace/workspace-ui.css；product.css抽出原controls；structural-symbols.js仅符号呈现。tests/endpoints/test_ui_phase2b1.py与tests/browser/test_ui_phase2b1.py。
**Interfaces:** 原id/data hook不变；#workspace-root新增ui-controls class，呈现CSS主动限四个阶段；图标使用shared/icon.html；structural-symbols签名/输入/命中域不变。
- [x] 运行baseline endpoint/CAD application tests；新增shell验收先RED（缺少分组、共用样式、带标签SVG）。
- [x] 左工具轨按绘图/编辑分组，移动真实transform-toolbar，右侧保留transform-panel/属性；命令区放Canvas下缘，精确输入保留details；视图工具靠近Canvas；底栏保留全部坐标/辅助/草稿来源。
- [x] 重用token/controls，图形以screen-space unit绘制，原位置/方向/数值及hit area不变；不加入Fixed能力。
- [x] 新shell、原workspace/CAD endpoint/application tests通过；保存/冲突/legacy/readonly保持。

### Task 2: Check / Prediction / Analyze呈现（W06–W08）
**Files:** 同workspace模板与workspace-ui.css；prediction.js只生成更清楚分组/heading，不改workspace数据/请求/状态条件。
**Interfaces:** 原choice/state与handler不变；四选aria-pressed保留，maximum/path/start/complete/skip控件各一份；check issue按钮仍指向原focus issue，分析从真实保存版本。
- [x] 新shell断言检查/预测/分析的层级、必要警告、状态语义先RED。
- [x] 阶段任务Inspector分段；预测四选/最大位移/路径/完成与跳过分开；分析说明事实与假定，不作安全合格结论；错误/忙碌保留原机制。
- [x] 相关prediction/workflow endpoint/application tests通过；不改数据契约。

### Task 3: 隔离环境、一次Browser Regression与交付
**Files:** 新增config/phase2b1_review_settings.py、scripts/run_phase2b1_review.py、scripts/verify_phase2b1_review.py；docs/development/issa-ui-phase2b1/。
**Interfaces:** 独立50586/private DB/cookies；先用真实SSR基准截图Before，再截实施After；不访问50442/50584。
- [x] 建新私人DB与真实v2教学模型，通过现有服务；保留Before三尺寸。
- [x] 完成后一次运行受影响Browser：CAD keyboard/toolbar/transform/core、check recovery、真实prediction/analyze/save/error、布局/focus/contextmenu/modal；已有Results入口smoke。
- [x] 失败留证，有界修复/相关重验；不改有效断言，不跑Full Browser/Mechanics。
- [x] W01–W08映射、Before/After、3尺寸、targeted结果与已知限制，下一阶段基准；独立review，无受保护路径diff。
- [x] 本地commit，环境可用，工作树干净，STOP等待Owner。


## 收尾调整与结果

- Owner追加：快捷键按钮只显示?；XY使用原点圆点与两支方向箭头，固定屏幕尺寸。
- 为容纳screen-space符号，Fit viewport做60 CSS像素包络适配，原reduceView/坐标/模型保持；因此不再要求inline脚本逐字一致，仅改import及两个Fit呈现调用。
- 64px输入reserve恢复；v1显式Connection支座继续原符号，v2用新版。
- SSR selector specificity恢复；正常旅程fixture日期动态有效，权限矩阵过期403断言保留。
- 130端点/应用通过；初次173 Browser中8失败均有界修正重验通过；最终7 UI、4旅程、40相关权限端点通过。详见docs/development/issa-ui-phase2b1/TARGETED_QA.md。
- 不执行Full QA、不merge/push/deploy；保留本分支与私人展示供Owner确认。
