# 校内结构设计学习平台 — POC V1

当前状态：**PRODUCT-ALIGNED — MANUAL OWNER ACCEPTANCE READY**。

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

权威公开控件旅程位于 `tests/browser/test_poc_v1_student_journey.py`。它覆盖 Login → 空白项目建模 → Prediction → Analyze → Compare / Explain → explicit-Run Report / Reasoning / Reflection → 第二次 Run → 历史切换。

## 明确边界

Euler 自动判断、任意角 Roller、复合截面重叠编辑、Frame/3D/非线性、自动优化、PDF/DOCX/Excel 导出与 AI 生成工程论证不属于 POC V1。开放决策与剩余人工验收见 `docs/specs/POC_V1_KNOWN_ISSUES.md`。
