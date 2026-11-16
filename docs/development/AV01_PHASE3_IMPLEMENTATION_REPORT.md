# AV-01 Phase 3 — Task 6–7 實作與驗證

日期：2026-11-13，Asia/Shanghai。分支：`feat/av01-phase3-results-integration`。
基準：`7f92e12f5d25421a7c64ca5b9a8fdfc60f2e9f8a`，核對乾淨後建立隔離 worktree。
本輪只授權原 TDD Plan Task 6–7；保留 Task 1–5，未實作 Task 8–10。

## 實作結果

**Task 6：Object Evidence / Hover。** 單一 Saved Run Object Evidence 同時供 Inspector、可存取物件清單及 Hover 使用。既有三種選取為 ANALYSIS_NODE、SUPPORT、ANALYSIS_SEGMENT。節點提供原始座標、實際 ux/uy 與位移大小；支座提供節點合計 Rx/Ry 及相關支座，不分攤反力；分析段提供保存軸力、原構件對應與全部 sibling segments。MIXED、ZERO_FORCE 及預測比較只呈現既有 M9 判定，不重新分類或平均。

學生標籤沿用 Snapshot resolver，簡體中文、必要單位、安全缺值及可展開完整保存值；不顯示內部 ID/hash/client key。鍵盤物件清單與 touch tap 提供完整選取等價入口。

Hover 穩定約 400 ms 顯示 2–4 個主要欄位；400 ms 仍為 visual calibration candidate。整棵 Tooltip `pointer-events:none`，不 capture、不搶焦點、不提供編輯。離開、目標改變、pointerdown/cancel、pan、wheel、Fit、隱藏、切分頁、destroy、Run/epoch 切換清除 timer/anchor/preview；Escape 關閉，離開再進入才恢復。pointermove 不重建整份 Evidence、不 redraw 完整 Canvas、不發新請求。

**Task 7：正式 Results 接線。** 在現有 Conclusion 掛載同一 readonly renderer；沿用 run-context 的 Selected Run selectionToken/epoch，不另建 Run 或 selection authority。成功 data/reveal 後建立 Project/Run/Revision/version/hash/schema anchor，獨立載入 Task 2 Visualization API；後續 teaching 尚未完成或不可用，合法數值圖仍可顯示。無既有 teaching maximum/classification 時關閉依賴圖層，不猜值。

Run 切換立即清圖、Hover、Inspector、舊請求；ABA、舊成功/錯誤/拒絕與 late-data 均受 token/generation 防護。權限拒絕清除受保護所選內容，網路失敗保留合法 M9 文字並提供同 Run retry。未改既有 Reflection ownership/completion、Explanation 或儲存契約。

Results 與 CAD Canvas 隔離：無幾何編輯、Grip、CAD 右鍵命令或 CO/M/RO/ST/LEN 執行；Escape/Shift/Space guard 僅作用於 Results，不破壞 Prediction pan 或 native checkbox。Results 顯示/隱藏、Fit、pan/zoom、resize，以及 Build 原有欄位配置均有測試。

既有 Conclusion/Compare/Why 構件按鈕轉向可見 readonly Evidence，僅依已投影 `physical_member_id` 找現有 ANALYSIS_SEGMENT；不改 hidden Draft selection，不產生新 identity mapping。晚到 teaching 在 available 與 HTTP200 unavailable 兩條路徑共用分頁／焦點恢復。

## RED → GREEN 紀錄

| 範圍 | 真實紀錄 |
|---|---|
| Fresh baseline | 364 relevant backend passed（含 131 Mechanics 子集）；117 existing Renderer/M9/KB Browser passed。QA 暫存路徑舊 prefix guard 造成一次 collection 中止，修 QA 設定，未算產品 RED。 |
| Task 6 | 30 missing-feature RED / 25 existing PASS；首次 47 PASS / 8 FAIL。修正 hidden→visible redraw、支座/反力命中優先序與水平 hit size；測試時鐘改為確實暫停。9 targeted PASS，116 component Browser PASS。 |
| Task 7 | 初次 14 RED / 14 fixture errors；修 fixture import 後 30 genuine RED / 1 existing prerequisite PASS。SVG 水平線 bbox、SVG textContent、雙 Canvas selector、等待合法 M9 overlay 與 readonly navigation 等測試問題均保留原始紀錄，未改幾何迎合測試。 |
| 接線缺陷 | Prediction Space pan 1 RED；Results 空白欄 3 RED；late teaching/Draft selection 焦點 1 RED。各最小修正後 targeted GREEN；整合前 153 AV Browser PASS。 |
| 獨立審查 | 兩個 Important：M9 按鈕目標 hidden Draft、HTTP200 unavailable 漏恢復分頁/焦點。新增 6 genuine RED 後修正。 |
| 支座圖示 | 父審查將「銷接/滾動共用相同符號」視為 Important 工程語意問題，3 RED；只依保存 PINNED/ROLLER-X/Y 畫方向，未知類型用中性標記。首次 GREEN 的 1 FAIL 是測試誤取 reaction hit midpoint，改用原始節點錨點。 |
| 廣泛 M9/CAD | 首次被中斷，>50% 至少 2 F、無完整結果，從未標 GREEN。新 DB diagnostic：52 PASS / 1 FAIL（222.01s），既有 public journey 發現新清單重用 M9 maximum-candidate hook，重複計數。新 hook 改 AV-01 namespace，原 M9 測試未改。 |
| 修正 targeted | 10 passed / 93 deselected（29.73s），包括原 public teaching journey。Deselected 不是 skip 或 PASS。 |

修正後全 AV 範圍初跑 161 passed / 1 failed（348.04s）：helper 的即時 painted-extent 判斷遇到同 epoch DOM 重掛載。保留相同幾何／stroke 條件，以有界等待實際完成繪製取代即時取樣。

廣泛 M9/CAD 另重現原中斷紀錄第二個 F：舊測試在 numeric-first placeholder 分頁顯示時擷取空表格，之後與完整三表比較。隔離 diagnostic 1 failed（6.63s）。僅新增等待完整三個保存表格再擷取；歷史提示與表格內容完全不變的斷言皆保留，產品未再改動。受影響重跑涵蓋全部 AV integration 與整份 M9 run-context；下表依實際完成結果更新。

## Fresh QA

| 本輪執行 | 結果 / 證據檔前綴 |
|---|---|
| AV Browser | 全範圍初跑 **161 passed / 1 readiness failed**（348.04s）；其中 119 Renderer/Evidence 案例通過。全部 43 integration 案例經 readiness 修正於下列重跑通過。— `post-review-av01-browser` |
| M9/CAD Browser | **286 passed / 1 readiness failed，1124.98s**；唯一失敗及整份 24-case run-context 已由下列重跑通過 — `post-review-m9-cad-browser` |
| 受影響 Browser 重跑 | **67 passed，252.30s**（43 AV integration + 24 existing M9 run-context）— `readiness-regression` |
| 相關 backend / permissions / Reflection / workspace / projection | **365 passed，37.56s** — `final-backend` |
| Mechanics | **131 passed，為上述 backend 的子集，不另加總** |
| Django check | **0 issues** — `post-review-django-check` |
| Migration dry-run | **No changes detected** — `post-review-migration-dry-run` |
| Diff / protected state | **diff check 通過；13 舊 worktrees、22 檔案與原 branch refs 無差異** |

以 JUnit identity 去重並以受影響重跑取代相同案例的舊結果，**449 個唯一相關 Browser 案例最新結果為 449 passed / 0 failed / 0 skipped**（AV 162、M9/CAD 287）。這是分批驗證覆蓋，不是單次 449-pass invocation，也不是全專案 suite。兩次初跑的非零 exit 與原始 failure 都保留於 `final-related-browser-coverage.json` 的 resolution 映射；67-case 重跑為 exit 0。所有批次開始時的 7 個產品檔 SHA-256 完全相同，且已與實作提交 tree 核對相符，未靠測試期間修改產品取得通過。

365-case backend 在 Task7 提交執行；其後只有前端及 Browser readiness 調整，backend/權限/模型零差異。Django check 與 migration dry-run 為審查修正後執行。

QA runner 為每個 Browser invocation 建立新的權限受限 test-owned file-SQLite DB；backend 使用隔離 memory settings。沒有使用 Owner DB/服務。完整命令、settings、DB 路徑、HEAD、開始時 source SHA、退出碼、日誌及 JUnit 保存於本 worktree ignored evidence directory：`.superpowers/sdd/2026-10-27-av01-analysis-visualization/`。防休眠 guard 隨每次 runner 結束釋放。

沒有重跑全專案 Browser/non-browser suite。過去的 551/816/22 skip 不當成本輪結果；22 項 file-SQLite concurrency skip 未由本輪選定子集驗證，不宣稱 concurrency PASS。

## 獨立審查與裁量

一次 fresh-context whole-diff 靜態審查：`7f92e12..5c96a1d` 全部 11 檔及直接相依；2 Important，無確認 Critical/Minor。兩項均以 RED→最小修正→GREEN 處理；其後為一次有界修正 pass，沒有以此代替 Task 9 最終全功能審查。原意見及處置保存在 `independent-review.md`。

審查明確未判定項目的處置：

- 最終標籤碰撞、Hover 校準與視覺接受度：父代理檢視三尺寸真實截圖；完整矩陣與 Owner 視覺裁決仍待 Task 8–10。支座符號則升為本輪 Important 窄範圍修正，非新增力學判定。
- 未變更 backend/legacy identity/mechanics/auth：本輪 relevant backend 已驗證支持路徑，無全面正確性宣告。
- 非法 numeric string formatter：正式 projection 已驗證數值，沒有確認的產品輸入路徑；不引入額外 coercion 或補零。
- numeric-only 歷史文案：顯示所選 Run，未聲稱等同 current Draft；無確認 regression，Owner copy review 仍待決。
- QA 數量／截圖品質：獨立 reviewer 未執行或看圖，由主代理保存實跑證據並檢圖，不冒稱獨立 QA。

執行裁量與代價：本輪明確 Task 6–7 授權優先於歷史 Phase1-only 狀態文字，工程 Spec/Plan 不改；保留 ignored 證據而非清理以供 Owner 查核（佔本機空間）；相關回歸按本輪授權執行，完整 suite 保留 Task 9；Task 6 雙 Canvas 隔離透過 Task 7 真實公開頁驗證，未以 fake editor 代替；bootstrap projectId 僅建立 data anchor、不改權限（不一致 fails closed）；CSS 僅 Results+AV root，基本三尺寸不等於最終視覺接受；numeric-first 為批准行為，測試等待完整保存表格而非空 placeholder（若永不載入會有界失敗，不設 skip 或條件式通過）。

## 真實 Chromium 畫面

位於上述 evidence directory 的 `screenshots/`：

- `task7-results-1024x768.png`、`task7-results-1280x800.png`、`task7-results-1440x900.png`：實際 viewport，Saved Run 原始/變形/反力及所選 segment Inspector；1024 堆疊、較寬尺寸並列。
- 同名 `-overview.png`：完整頁面補充；不是另一個 viewport。每張 `.json` 記錄尺寸、公開頁 URL 與拍攝時 HEAD；`public-screenshot-index.json` 保存 PNG SHA-256。
- `task7-results-hover-1280x800.png`：真實公開 Results 的 segment Hover；為可重現生命週期使用暫停時鐘，不代表人工 timing acceptance。
- `before-layout-*`：原 Results 留空白欄的修正前證據。

公開畫面來自合成帳號的公開 UI Save/Reload/Check/Analyze 與 genuine Solver Saved Run；沒有 DOM 注入幾何。API mismatch/late response 等控制案例在測試中另行標示，不冒稱自然 Solver 情境。截圖可能在提交前拍攝；runner source hashes 對應經測試 working blobs，提交後另核對不變。測試 server 已隨案例結束，不提供失效的測試 URL 作 Owner runtime。

## 文件、保護與變更

MASTER_SPEC v1.12、已批准 Spec/Plan 本輪皆逐位元組不變：

| 檔案 | SHA-256 |
|---|---|
| MASTER_SPEC | `bff6e669234c5985e576fa2f8b81ab9108acddb3e7950209884503838c226f3a` |
| 本分支正式 Spec | `90f686790cdf989ed3a5258efe4fdfd4e2c6a0144267e6d1146f3a701b92fd52` |
| 本分支正式 Plan | `22cdf3ab955ca9607b4f5efd625f31cb2ec5cd63174d22f95f49b76a793dc023` |
| 原 M9 untracked Spec | `b4fff4cc644bc6d72aa8b7f11ebf1abfea03126599ef710319ddc59b60865da5` |
| 原 M9 untracked Plan | `ebb7e1075f0ff4eff605cf3365cdb715c463690bbeb7fb6a6d51da6edbdd8d98` |

正式文件含既有 Phase1 狀態同步，與原保管來源不同；本輪未同步或覆寫。保護清單原有 dirty/untracked 狀態完整保留。

本輪 12 個變更檔：`analysis-visualization.js`、`analysis-visualization-renderer.js`、`analysis-visualization.css`、`results.js`、`run-context.js`、`workspace.css`（皆 `projects/static/projects/workspace/`）；`templates/projects/workspace.html`；`tests/browser/av01_harness.py`、`test_av01_layers_evidence.py`、`test_av01_run_integration.py`、`test_m9_run_context.py`；本報告。

提交：Task6 `e49965e5a143be0ec31f44b2639113d6e28e20d4`；Task7 `5c96a1d3b10cf82a6823a6eb3f8911c68d0c294f`；審查修正 `4746ed5ae3eea7a2cadeedaf9202fbaf03351222`。本報告為後續 docs-only 提交；最終完整 HEAD 由 Git history / 交付訊息提供，避免文件自我雜湊循環。無 Solver/Mechanics/domain/schema/API/儲存值修改，無其他 worktree 或 Owner DB 操作，無 merge/push/deploy。

## 尚待批准與風險

- Task 8：完整視覺 A–K 矩陣、校準與人工視覺接受；本輪基本三尺寸不取代此工作。
- Task 9：最終完整 regression / whole-branch review；本輪相關回歸不冒充 full suite。
- Task 10：Owner handoff / checklist 與正式驗收；未建立本輪 Owner runtime。
- 真實中文 IME、輔助科技／觸控硬體與瀏覽器 redirect 型 session-expiry 尚未於此新增驗證；原 transport/auth 未重寫。明確 401/403/PURGED 與 Manager/Developer/GRACE、private Reflection 支持路徑已測。
- M9/CAD 完整 Owner Acceptance：PENDING；Teacher Review：DEFERRED；沒有 Teacher PASS 或 merge/release/deployment approval。

**AV-01 PHASE 3 — TASK 6–7 IMPLEMENTED, QA VERIFIED, OWNER ACCEPTANCE PENDING**

依 Owner 指示保留分支及證據，不 merge/push/deploy，不清理 worktree，不啟動後續 Tasks。
