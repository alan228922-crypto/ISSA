# ISSA UI Phase 2A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将已获授权的v1.1设计接入所有一般SSR页，保留真实后端及既有权限/数值契约。

**Architecture:** 共用SSR base、字段/通知/图示partial与独立作用域的产品CSS；Workspace只消费新的共享Header及tokens，不接入新SSR的全局排版。截面输入/预览API及竞赛确认服务保持原行为，仅调整图形和错误页面呈现。

**Tech Stack:** Django Templates、CSS、原生JavaScript、SVG、pytest-django、Playwright；无新依赖或CDN。

**Spec:** design/issa-product-uiux-v1 @7933932deb4a23fe4d377552854342cd48db3f5d 的六份设计/交付文件；正式产品基准231a1379764d53f5679b4051d4f5a09ef5cc7832；本计划为新实施记录，不修改批准Spec/Plan。

## Global Constraints

- 简体中文；不改变Solver/Mechanics、Schema/Permissions、AnalysisRun/Revision、CAD命令/状态机或M9/AV-01契约。
- 不操作Owner Runtime50442及原DB、其他工作树、未提交CAD修改；不merge/push/deploy。
- 只拷贝经过批准的tokens/图标/品牌资产，不导入设计fixture、mock业务逻辑或合成工程数据。
- 使用私人DB、独立端口与cookie的review环境；测试DB独立；保留所有失败日志，不放宽原有效断言。

## Review Focus

- 共享Header不能把新CSS reset泄露到旧Workspace/Results。
- 很长的真实名称/科学记号与表格只能局部滚动，不能遮住提交/取消。
- 密码/预览凭证不在确认或错误页回显；错误保留原HTTP状态。
- 截面输入改变立即清除旧属性/形心；返回旧请求不能覆盖新输入。
- CSV/单笔管理操作仍两步确认、readonly、noop、访问策略不变。

## Task 1 — 共用shell与账号/项目

Files: 新增projects/static/ui/{tokens,product,header}.css、forms.js、icons.svg及资产；templates/shared/{base,form_field,form_errors,icon,footer}.html；修改shared/product_header.html、accounts三页、project_create.html。Tests: tests/endpoints/test_ui_phase2a.py、既有event_landing/project_creation/workspace tests。

Interfaces: SSR shell使用ui_shell=True；新样式限.issa-ui及.issa-header；保留原表单action/name、CSRF、输入值与next；Header供旧Workspace消费。

- [x] 先运行新shell/关联错误测试，确认基准缺少设计框架而失败；记录RED。
- [x] 实现上述共用层与所有账号/项目模板；不更改认证或项目创建服务。
- [x] 运行针对账号/项目/入口的endpoint tests，确认GREEN；记录结果。

## Task 2 — 材料/截面/条材

Files: templates/materials全部六页；materials/static/materials/section-designer.js与仅绘图module。Tests: material_pages/projects_sections；新截面客户端验证纳入最终Browser集合。

Interfaces: 保留data-section-designer/data-preview-url、formset前缀、data组件挂钩及section-properties-v1响应；图形模块仅消费rectangles和后端properties，不求截面性质。

- [x] 用既有endpoint tests确认写入、只读及删除影响基准；新增动态图形验收后再改图形。
- [x] 统一catalog/全部新建编辑/删除/指派页；屏幕像素描边、真实比例/旋转、后端形心与独立属性表。
- [x] targeted material/section endpoints与前端纯绘图断言通过；保留异常响应/过期状态不显示旧值。

## Task 3 — 赛事管理

Files: templates/competitions全部九模板/片段、shared/request_error.html；competitions/views.py及materials/views.py仅错误响应呈现。

Interfaces: 两步preview_ref、operation、CSV字段/限制、PRG通知和状态码不变；无新管理能力。

- [x] 新管理错误shell测试先RED；既有participant/provision tests作业务边界。
- [x] 实现导航、所有表单/确认/结果/CSV及readonly/error呈现；不改变服务/鉴权。
- [x] targeted management endpoints/application tests通过，敏感数据无回显。

## Task 4 — 隔离展示与受影响Browser Regression

Files: 新增config/phase2a_review_settings.py、scripts/run_phase2a_review.py；tests/browser/test_ui_phase2a.py；docs/development/ISSA_UI_PHASE2A_*。

Interfaces: review环境只绑定127.0.0.1:50584；专用临时目录及DB、issa_phase2a_session/issa_phase2a_csrf；不复用正式DB。种子资料通过现有模型/服务建立，不伪造分析结果。

- [x] 建立一次性私人DB，运行迁移/种子与真实服务器；保留基准Before图片及最终After。
- [x] 一次运行受影响Browser集合：entry/project creation、participant management、section designer、新三尺寸/焦点/真实提交及workspace/results入口检查。
- [x] 只在有失败时针对根因补验；不跑Full Browser/Mechanics Suite，不弱化断言。
- [x] 逐项映射38项Inventory：2A完成与2B/2C保留；记录targeted QA计数、范围、已知问题和review访问方法。
- [x] 最终独立review、验证受保护路径无diff、提交本地commit并STOP。

## Implementation decisions

- 原CSV结果是PRG回到队伍列表的processed/noop通知；保留该实际流程，统一样式，不添加伪造结果数。
- 截面绘图单独模块只做坐标/旋转/标注；后端仍是属性权威。
- 现有Browser fixture使用隔离浏览器context和sessionid；测试沿用，独立展示环境另用专用cookie名称。
