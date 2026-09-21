# 本机 Demo 数据

仅在本机开发设置（`DEBUG=True`）下运行：

```bash
python3 manage.py seed_demo --confirm
```

该命令创建或复用明确标识的 `demo_student`、Demo 赛事，以及两个项目：

- `B/T01 桁架 Demo`：预置可检查、可分析的 B/T01 草稿；
- `空白建模 Demo`：用于验收材料、矩形截面和第一根构件的真实创建流程。

命令不会自动执行分析，也不会创建 Prediction、Reasoning 或 Reflection。它会输出登录信息、Events 入口、两个 Workspace URL 和手动验收顺序。重复运行不会重复创建这些记录。命令拒绝在 `DEBUG=False` 下运行，不能用于 production provisioning。

建议先执行：

```bash
python3 manage.py runserver
```

随后使用命令输出的本机账号登录，从 `/events/` 进入项目。预置项目用于验收 Model Check → Prediction → Analyze → Compare / Explain → Report → Reasoning → Reflection；空白项目用于验收 Material / Section → Node / Member → Save / Reload。
