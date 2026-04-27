# Story 005 — 主動預警與週期性績效彙整

## User Story
- **As** 部門主管
- **I want** 系統自動在 deadline 前提醒、review 延遲時告警、月底自動產月報、季度推送 PM Review
- **So that** 績效機制是「自動運作」而非「主管定期手動巡」；異常在發生當下被攔截，而不是月底回顧才發現

## 成功指標
- Deadline 將至自動提醒（避免 surprise-delay）
- Review 延遲（PR 卡住、issue 未回）自動告警
- 每月自動產出該月績效彙整（不用手動跑腳本）
- 每季度自動產生 PM Review issue，使用統一模板
- 所有 cron workflow YAML 解析正確，schedule 排程穩定

## 涵蓋 Features
- [x] perf-deadline-reminder workflow — workflow 已上線
- [x] perf-review-lag workflow — workflow 已上線
- [x] perf-monthly-review workflow + 2026-04 月報自動產出 — commit `98d1602`
- [x] quarterly-pm-review issue template + PM 績效三層架構 — commit `57d8877`
- [x] 4 個 cron workflows YAML 修正 — commit `39f4aba`
- [x] reopen 事件處理（與 cron 共用基礎建設） — commit `54d1af2`

## 相關既有功能
- `.github/workflows/perf-deadline-reminder.yml`
- `.github/workflows/perf-review-lag.yml`
- `.github/workflows/perf-monthly-review.yml`
- `.github/ISSUE_TEMPLATE/quarterly-pm-review.md`
- 共用 `PERF_TOKEN` 與 `employees/*.yml`、`perf-labels.json`

## 相關 commits
- `57d8877` perf v5.3：需求變更機制 + PM 績效三層架構（季度 PM Review issue template）
- `98d1602` perf: 月報 2026-04 自動產出
- `64d08c2` fix(validate): schema 加 system_type enum
- `39f4aba` fix(workflows): YAML 解析錯誤——4 個 cron workflows 修正
- `54d1af2` perf v5.1 Phase 2：cron workflows + reopen 事件處理

## 備註
- Cron 排程都跑在 GitHub Actions runner，免維護自架 scheduler
- 所有提醒類 workflow 共用同一份 `perf-labels.json` 與 `employees/*.yml`，邏輯與 Story 002/001 強耦合
- 月報目前是 `commit` 形式入庫；如果未來改成發 issue，要新增對應 workflow output
- Quarterly review 是季度節奏，預計每三個月觸發一次
- Dashboard 個人頁（page2）已加 Layer 3 區塊串接 `perf:quarterly-review` issue（僅 PM 角色顯示），實作見 Story 004 commit `627c5e9`
