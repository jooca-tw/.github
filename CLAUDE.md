# CLAUDE.md

本 repo 採 **stories（需求層）+ code（實作層）** 雙層結構。

## 動工前先讀

- **`stories/README.md`** — Story 索引、目錄結構、新需求流程、skill 對照表
- **`README.md`** — 系統現況（5 維度、16 perf labels、員工 schema、workflows）

## 新需求流程

歸屬到 `stories/NNN-slug/` → 建 `features/<slug>/` → `/spec` → `/plan` → `/build`。

對應 skill：
- 寫 SPEC：`spec-driven-development`
- 寫 plan：`planning-and-task-breakdown`、`api-and-interface-design`
- 實作：`incremental-implementation`、`test-driven-development`
- Review：`code-review-and-quality`

模板位於 `stories/_templates/`。

## 規矩

- 既有功能 **不補 SPEC.md**——code 為真相，只有新需求走 spec 流程。
- Feature 完工後，回去 `STORY.md` 打勾並附 commit hash。
- 動 `performance/employees/*.yml`、`perf-labels.json`、`.github/workflows/` 前先確認對應 Story 的成功指標不會被破壞。

## 當前 active feature

（無——目前所有 Story 都是 ✅ 已上線狀態，新需求進來時在這裡指向 `stories/NNN-slug/features/<slug>/plan.md`）
