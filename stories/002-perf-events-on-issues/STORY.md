# Story 002 — 以 GitHub Issue 作為績效事件的事實基礎

## User Story
- **As** 部門主管
- **I want** 用 `perf:*` label（紅旗扣分／綠旗加分／tier 難度）在組織任何 repo 的 issue 上標記事件，分數定義集中維護並可同步全 org
- **So that** 績效有可追溯、可審視的客觀事件，而非主觀印象；事件本身就是工作流程的一部分（issue 本來就要關），不另外開系統

## 成功指標
- 所有 perf label 集中定義在 `performance/perf-labels.json`，含 `score` / `dimension` / `role` / `auto` / `type`
- 一行命令（`sync-perf-labels.sh`）即可把標籤集同步到組織所有 repo
- Label 異動只改一處（本 repo），不需逐 repo 編輯
- 涵蓋三軸（事件類型 × 維度 O1-O5 × 角色 RD/PM/All），分類能對應到考核制度文件
- 客戶插單／需求變更等灰色地帶有專屬 label，不會被簡化成「都算 PM 扣分」

## 涵蓋 Features
- [x] 16 個 label 定義（6 紅旗 / 5 綠旗 / 5 tier） — commit `851ac87`
- [x] sync-perf-labels.sh 同步腳本 — commit `821c9c7`
- [x] v5.1 三軸架構（label / prompt / AI Collab CI lint） — commit `fe52365`
- [x] v5.2 客戶插單拆三級 + 加分機制 — commit `0d63987`
- [x] v5.3 需求變更機制 + PM 績效三層架構 — commit `57d8877`

## 相關既有功能
- `performance/perf-labels.json`
- `performance/sync-perf-labels.sh`
- 三軸 dashboard（Story 004）讀取這些 label 計分
- AI auto-label（Story 003）依 `auto: true` 規則自動套用

## 相關 commits
- `57d8877` perf v5.3：需求變更機制 + PM 績效三層架構
- `0d63987` perf v5.2：客戶插單變更管理機制
- `fe52365` perf v5.1 Phase 1：三軸架構 label / prompt / AI Collab CI lint
- `821c9c7` 新增 sync-perf-labels.sh
- `851ac87` 新增 perf-labels.json

## 備註
- 綠旗（bonus）目前都 `requires_confirm: true`，不讓 AI 自動加分，避免被刷
- Tier label 是 meta，不直接計分，只標記專案難度供主管判斷
- 後續要加新 label 時務必同步更新 `auto-label.py` 的 prompt 與 dashboard 的計分邏輯
