# 校内结构设计学习平台 — POC V1

当前状态：**UX V2 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING**。UX V2 已将 POC V1 的技术原型整理为以学生学习过程为主的界面；这不代表 Product Owner 已完成人工验收。

这是一个 Django + Vanilla JavaScript 的 Truss-first 教学 POC。P0 仅支持二维线弹性、小位移、铰接、轴向受力桁架；单位为 mm / N / MPa / g。浏览器负责交互与呈现，所有授权、版本、分析和力学事实由服务端及纯 Python mechanics 层保持权威。

## 本机启动

```bash
python3 manage.py migrate
python3 manage.py seed_demo --confirm
python3 manage.py runserver
```

`seed_demo` 仅在 `DEBUG=True` 可用，会输出本机账号，并提供预置 B/T01 项目与空白建模项目。登录后从 `/events/` 进入，不要把该命令用于生产 provisioning。

## 验证

```bash
pytest -q -m 'not browser'
pytest tests/browser -q -m browser
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
python3 manage.py migrate --plan
```

权威公开控件旅程位于 `tests/browser/test_poc_v1_student_journey.py`，UX V2 阶段与总结隔离回归位于 `tests/browser/test_ux_v2_student_journey.py`。学习流程为建模 → 检查 → 预测（可选）→ 分析 → 理解 → 总结；总结中的计算依据、我的设计说明和反思始终针对显式选中的同一次分析。

## 明确边界

Euler 自动判断、任意角 Roller、复合截面重叠编辑、Frame/3D/非线性、自动优化、PDF/DOCX/Excel 导出与 AI 生成工程论证不属于 POC V1。开放决策与剩余人工验收见 `docs/specs/POC_V1_KNOWN_ISSUES.md`。
