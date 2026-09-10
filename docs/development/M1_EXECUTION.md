# M1 執行紀錄

依 docs/specs/CODEX_IMPLEMENTATION_PLAN.md 已核准順序執行 1 → 6 → 7 → 11 → 12 → 13 → 14 → 15。
每一任務先測試失敗，再最小實作、target/full regression、diff 檢查、獨立 commit。
不修改 MASTER_SPEC，不建立 Django apps，不進入 M2。

- [x] Task 1：package import / architecture guard、最小專案設定。
- [ ] Task 6：rectangle 解析 properties。
- [ ] Task 7：non-overlap composite、面積重心與平行軸定理。
- [ ] Task 11：純資料契約與 machine-readable validation。
- [ ] Task 12：4×4 element stiffness、global K/P、DOF mapping。
- [ ] Task 13：restrained solve、u/R/N、B/T01、singular failure。
- [ ] Task 14：B/T02/B/T03；B/T04 等待可信 reference。
- [ ] Task 15：stress / mass / explicit-input Euler。

## 環境

本次使用 python3（Python 3.13.14）及已安裝 NumPy 2.5.1、pytest 9.1.1。
專案直接依賴版本定義於 pyproject.toml；web optional group 保留 Django 5.x 路線。
新環境可使用 `python3 -m venv .venv`，接著 `.venv/bin/python -m pip install -e '.[test]'`。
M1 不要求 Django setup；SQLite 留給未來 persistence。未建立 migration/database。

## Task 1

RED: `python3 -m pytest tests/contracts/test_architecture_boundaries.py -v`
→ 2 failed，缺少 mechanics package（exit 1）。
GREEN / regression: `python3 -m pytest -v` → 2 passed（exit 0）。

## B/T04 gate

BLOCKED — MISSING TRUSTED BENCHMARK REFERENCE。
現有 repository/specs 僅有驗收要求，沒有可信數值 fixture。不得由新 solver 自行生成 expected values。
