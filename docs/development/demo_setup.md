# 本机 Demo 数据

仅在本机开发设置（`DEBUG=True`）下运行：

```bash
python3 manage.py seed_demo --confirm
```

该命令创建或复用明确标识的 `demo_student`、Demo 赛事和 B/T01 可分析桁架草稿；不会自动执行分析，也不会创建 Prediction 或 Reflection。命令输出本机登录信息与 Workspace URL。它拒绝在 `DEBUG=False` 下运行，不能用于 production provisioning。
