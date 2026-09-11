# M1 執行與驗證紀錄

## 狀態與授權

**M1 STATUS: COMPLETE**。Task 14 的 B/T04 已使用 Product Owner 提供的解析闭式参考完成验证。
全部已授权的 mechanics benchmark gate 均已关闭。

**SPEC UPDATE REQUIRED — Platform Language = zh-CN**。本记录遵循当前产品指示：平台默认语言为简体中文；尚未修改 `docs/specs/MASTER_SPEC.md`，等待 Product Owner / System Architect 同步正式规格。

工作目錄：`/Users/user/Documents/developement/ＩＳＡＡ/.worktrees/m1-truss-mechanics`
分支：`feat/m1-truss-mechanics`
基線：`99f4985643f734f03ab08fd21a1b401c198e84b2`

依 `docs/specs/CODEX_IMPLEMENTATION_PLAN.md` Tasks 1、6、7、11–15 執行。
沒有修改正式 specs，沒有建立 Django apps、ORM、migrations、UI、資料庫，也未進入 M2。
使用 using-superpowers、既有 worktree 驗證、TDD、systematic-debugging、requesting/receiving-code-review、verification-before-completion 工作流程。
既有規格與本次明確授權已構成設計與執行核准，沒有重開產品設計。

## 任務與規格對照

| Task | 結果 | 對應條款 / 驗收 |
|---|---|---|
| 1 | 已驗證 | Master §13/32，mechanics 不依賴 Django；獨立行程遞迴 import 與 AST guard |
| 6 | 已驗證 | Master §10；rectangle A/centroid/Ix/Iy/mass、座標軸比較 |
| 7 | 已驗證（non-overlap） | Master §10.6/O-005；對稱/非對稱組合、旋轉、平行軸定理；重疊不支援 |
| 11 | 已驗證 | Solver Contract §4–8/13；不可變純值模型、穩定 error code、無 ORM |
| 12 | 已驗證 | Master §5；Solver Contract §9/11；4×4 剛度、方向餘弦、K/P/DOF mapping |
| 13 | 已驗證 | Solver Contract §10/15/16；B/T01、u/R/N、支承載重、singular failure |
| 14 | 已验证 | B/T02/B/T03、重排不变性与 B/T04 三杆超静定解析基准均通过 |
| 15 | 已驗證（formula only） | Solver Contract §17–19；N/A、ρAL、explicit E/I/L/K Euler；O-001 保持 open |

## 環境與重現

本次使用 `python3`：Python 3.13.14、NumPy 2.5.1、pytest 9.1.1。
環境亦已裝 Django 5.2.17、pytest-django 4.14.0；mechanics 不需要它們初始化。
`pyproject.toml` 明確要求 Python >=3.12，直接數值依賴 NumPy；test/web 分為 optional groups。
本次使用既有 interpreter，未宣称已有獨立 virtualenv 或所有 transitive dependencies lock。
新環境可使用：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -v
```

這是建議的重建指令，本次並未另行執行安裝。M1 不需要 Django setup。

## TDD 證據

所有下列命令均於指定 worktree 執行。每個 RED 均先於相應 production implementation。

### Task 1

- RED：`python3 -m pytest tests/contracts/test_architecture_boundaries.py -v`
- 2 failed，缺少 mechanics package，exit 1。
- GREEN/regression：`python3 -m pytest -v` → 2 passed，exit 0。

### Task 6

- RED：`python3 -m pytest tests/mechanics/benchmarks/sections/test_rectangle.py -v`
- 9 failed，缺少 mechanics.sections，exit 1。
- GREEN：同一命令 → 9 passed，exit 0。
- Regression：`python3 -m pytest -q` → 11 passed，exit 0。

### Task 7

- RED：`python3 -m pytest tests/mechanics/benchmarks/sections/test_composite.py -q`
- 9 failed，缺少 composite_properties，exit 1。
- GREEN：`python3 -m pytest tests/mechanics/benchmarks/sections/test_composite.py -v` → 9 passed，exit 0。
- Regression：`python3 -m pytest -q` → 20 passed，exit 0。

### Task 11

- RED：`python3 -m pytest tests/mechanics/unit/test_truss_validation.py -q`
- 最初 fixture import 造成 35 setup errors；將 import 移至 test-body helper 後重跑，35 failed，缺少 mechanics.truss2d，exit 1。
- GREEN：同一命令 → 35 passed，exit 0。
- Regression：`python3 -m pytest -q` → 55 passed，exit 0。

### Task 12

- RED：`python3 -m pytest tests/mechanics/unit/test_truss_stiffness.py tests/mechanics/unit/test_truss_assembly.py -q --tb=short`
- 8 failed，缺少 assembly module，exit 1。
- GREEN：相同測試路徑，使用 `-q` → 8 passed，exit 0。
- Regression：`python3 -m pytest -q` → 70 passed，exit 0。

### Tasks 13 / 14

為讓多桿 benchmark 也在 solver 尚不存在時取得 RED，先建立兩份 benchmark，再實作 Task 13；提交仍分為 Task 13 與 Task 14。

- RED：`python3 -m pytest tests/mechanics/benchmarks/truss2d -q --tb=short`
- 10 failed：Task 13 的 7 個、Task 14 的 3 個，均缺少 solver module；1 skipped（B/T04），exit 1。
- Task 13 GREEN：`python3 -m pytest tests/mechanics/benchmarks/truss2d/test_single_bar.py -v` → 7 passed，exit 0。
- Task 14 GREEN（原始范围）：`python3 -m pytest tests/mechanics/benchmarks/truss2d/test_planar_benchmarks.py -v` → 3 passed、1 skipped，exit 0。
- Regression：`python3 -m pytest -q` → 80 passed、1 skipped，exit 0。
- M1 correction：Product Owner 提供 B/T04 的闭式解析参考后，先新增测试。首次运行中，位移与杆力断言直接通过；反力断言因 `pytest.approx` 不支持字典内嵌元组而失败。改为逐支座比较，未改变生产代码或 tolerance；随后 `test_planar_benchmarks.py` → 4 passed，exit 0。

### Task 15

- RED：`python3 -m pytest tests/mechanics/unit/test_stress_mass.py tests/mechanics/benchmarks/stability/test_euler_explicit_k.py -q --tb=short`
- 46 failed，缺少 postprocess/stability module，exit 1。
- GREEN：相同測試路徑，使用 `-q` → 46 passed，exit 0。
- Regression：`python3 -m pytest -q` → 126 passed、1 skipped，exit 0。

## 獨立 review 與修正證據

Read-only reviewers 分別檢查 Task 1/6/7、Task 11–14、Task 15。

1. **旋轉邊緣接觸**：4° 共邊矩形被精確 SAT 比較誤判為重疊。先加回歸，1 failed/12 passed；修正投影比較為 8 ULP 捨入容差，13 passed。可分辨的正面積重疊仍拒絕；不修改 benchmark tolerance。
2. **Rectangle 數值範圍**：極大尺寸回 NaN 或拋原始 OverflowError。先重現 3 failed/9 passed，再在輸入與結果加 NUMERIC_RANGE，section suite 25 passed、全套 62 passed。
3. **Truss 直接 validation 超大整數**：10**400 造成 math.isfinite 轉換溢位。先重現 4 failed/35 passed，再回穩定欄位 issue；validation 39 passed，全套 130 passed/1 skipped。
4. **Composite 平行軸項溢位**：中心間距 1e154/1e200 產生 Inf/OverflowError。先重現 2 failed/13 passed，再檢查 aggregate 結果範圍；composite 15 passed，全套 132 passed/1 skipped。

Review 沒有發現其他 Important/Critical solver 或 Task 15 公式問題；上述發現均已修正。

## Benchmark 的獨立來源與 tolerance

| Benchmark | 狀態 | Expected 來源 |
|---|---|---|
| B/T01 | PASS | δ=PL/EA；1000 N、1000 mm、200000 MPa、100 mm² 得 .05 mm；N=P、R=-P，另測受壓 |
| B/T02 | PASS | 三角桁架節點平衡：R=P/2、N斜=-P/√2、N底=P/2；伸長相容得頂點 (.025,-.025-.05√2) mm |
| B/T03 | PASS | 幾何及節點載重鏡射對稱；總載重200 N→兩支座各100 N；對稱桿力、位移不變性 |
| B/T04 | PASS | 对称三杆超静定桁架的闭式解析式：uy=-P·h/[EA(1+1/√2)]；N_DB=-P(2-√2)，N_AB=N_BC=-P(1-1/√2)；反力与全局平衡逐项验证 |
| B/S01 | PASS | rectangle A=bh、Ix=bh³/12、Iy=hb³/12；對稱/非對稱面積重心與平行軸手算常數 |
| B/E01 | PASS | EI/L²=2 N；K=1,2,.5 分別得 2π²、.5π²、8π² N |

Expected 沒有呼叫 production function 生成。解析/benchmark 註解直接寫在測試中。
截面/Euler 使用 rtol=1e-12、atol=1e-12；單桿位移 rtol=1e-10、atol=1e-12 mm，力 atol=1e-9 N；多桿 rtol=1e-8，位移 atol=1e-10 mm、力 atol=1e-8 N。
沒有為通過測試而放寬上述 tolerance。

## B/T04 correction result

几何为 A(-1000,0)、B(0,1000)、C(1000,0)、D(0,0) mm；AB、BC、DB 的 E=200000 MPa、A=100 mm²，A/C/D 全约束，B 施加 Fy=-10000 N。解析期望值全部由提供的闭式方程计算，未调用 production solver 生成 fixture。

| 项目 | 解析期望 | 实际观察 | 差值 |
|---|---:|---:|---:|
| B ux (mm) | 0 | 0 | 0 |
| B uy (mm) | -0.2928932188134525 | -0.2928932188134525 | 0 |
| N_AB / N_BC (N) | -2928.9321881345254 | -2928.932188134525 | < 1e-12 |
| N_DB (N) | -5857.864376269049 | -5857.86437626905 | < 1e-12 |
| A Rx / Ry (N) | 2071.0678118654755 / 2071.0678118654755 | 2071.0678118654746 / 2071.0678118654746 | < 1e-12 |
| C Rx / Ry (N) | -2071.0678118654755 / 2071.0678118654755 | -2071.0678118654746 / 2071.0678118654746 | < 1e-12 |
| D Rx / Ry (N) | 0 / 5857.864376269049 | 0 / 5857.86437626905 | < 1e-12 |
| 全局平衡残差 (Fx, Fy) N | 0 / 0 | 0 / -9.094947017729282e-13 | < 1e-12 |

## Fresh Verification — 2026-09-11

M1 correction 已完成完整回归验证。

| Command | Collected | Passed | Failed | Skipped | Exit |
|---|---:|---:|---:|---:|---:|
| `python3 -m pytest tests/mechanics/benchmarks/truss2d/test_planar_benchmarks.py -v` | 4 | 4 | 0 | 0 | 0 |
| `python3 -m pytest tests/mechanics/benchmarks/truss2d -v` | 11 | 11 | 0 | 0 | 0 |
| `python3 -m pytest tests/mechanics -v` | 131 | 131 | 0 | 0 | 0 |
| `python3 -m pytest tests/contracts/test_architecture_boundaries.py -v` | 2 | 2 | 0 | 0 | 0 |
| `python3 -m pytest -v` | 133 | 133 | 0 | 0 | 0 |

`git diff --check` 通過。正式 `docs/specs/` 相對 documentation baseline 無變更。
AST import 檢查 + `rg -n 'django|FRAME_2D|\brz\b|Fixed|UDL|bending|shear|moment' mechanics` 無命中（rg exit 1 表示 no matches）。
Architecture test 另以全新行程攔截 Django import，遞迴匯入所有 mechanics 模組。

## 數值與中文註解

- +x 向右、+y 向上；N>0 受拉、N<0 受壓，stress 同號。
- 固定 mm/N/MPa/g；密度 g/mm³、截面 mm²/mm⁴。
- DOF 依 input node sequence：`[N0.ux,N0.uy,N1.ux,N1.uy,...]`。
- `assembly.py` 說明 EA/L、c/s、4×4 投影、全域 mapping；`solver.py` 說明零位移支承、尺度化、R=Ku-P、軸力回復。
- Public mechanics APIs 與資料類別有繁體中文 docstring；tests 註明獨立公式來源。
- 未添加逐行翻譯式低資訊註解；English identifiers 與 unit suffix 保留。
- 零長度 threshold=1e-9 mm；ZERO 軸力預設 tolerance=1e-9 N，僅分類，不改寫原值。
- 截面 strong/weak 僅比較重心 x/y 座標軸，並非一般主軸，更不是 Euler 控制軸政策。

## 保留的 gates / 限制

- O-001：只做 explicit E/I/L/K；無 default K、自動控制軸、最終風險等級或教學文案。
- O-005：只計算非重疊矩形；重疊回 OVERLAP_UNSUPPORTED。
- O-002：僅實作已指定 solver ux/uy flags；未決定 Roller UI/JSON 方向。
- O-003/O-004 未進入 M1，維持不變。
- SPEC CONFLICT：None。B/T04 的可信解析基准已由 Product Owner 提供并验证，不再是 SPEC GAP。
- 數值 singular 檢查使用 diagonal scaling + float64 rank/solve；近奇異病態模型可能拒絕，並非完整機構診斷。
- M1 無 ModelRevision/AnalysisRun/Hash persistence；那些屬後續任務，不宣稱完整分析流程已完成。
- 本次沒有獨立環境重新安裝驗證或大型模型效能測試。

## Git / 停止點

每一 task 與 review fix 有獨立 commit，沒有 merge/push/remote 操作。
保留 `feat/m1-truss-mechanics` 與現有 worktree，main 留在文件基線。
M1 已验收：B/T04 解析基准已关闭唯一未完成 gate。
本輪停止，不進入 M2。
