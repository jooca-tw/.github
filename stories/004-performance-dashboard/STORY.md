# Story 004 — 全員績效即時可視化儀表板

## User Story
- **As** 部門主管
- **I want** 一個每日自動更新、跨 repo 彙整、含部門總覽／個人頁／警示頁的網頁
- **So that** 1:1 或季度 review 前 30 秒就能掌握每個人的狀態，不用手動跑 SQL／翻 issues

## 成功指標
- 每日 00:00 UTC 自動重算；issue label 變動時也即時觸發
- Dashboard 部署到 GitHub Pages（gh-pages 分支），免本地起服務
- 三軸視圖（員工 × 維度 × 時間）對應 v5.1 三軸架構
- 個人頁 issue 可點擊跳到原始 issue（不需主管手動找 repo）
- 資料 schema 穩定（`stats / members / alerts / alert_summary`），前後端解耦

## 涵蓋 Features
- [x] 資料產生器（跨 repo 抓 perf issues → data.json） — commit `b7d1c9f`
- [x] dashboard workflow（cron + issue 觸發 + 部署） — commits `7e5ec6b` `3c7e26d` `ccfe930`
- [x] 資料 schema 對齊 dashboard 需求 — commit `168b481`
- [x] 前端三頁（總覽 / 個人 / 警示） — commits `c0a75ae` `ce8c23d` `15da6ec` + `397690b`（CSS）+ `6620a3e`（JS）
- [x] 個人頁 issue 超連結 — commit `ad57679`
- [x] v5.1 Phase 2 三軸 dashboard 重構 — commit `54d1af2`

## 相關既有功能
- `performance/scripts/generate-dashboard-data.py`
- `performance/dashboard/{page1,page2,page3}.html`、`app.js`、`style.css`
- `.github/workflows/performance-dashboard.yml`（部署 gh-pages）
- 讀 `employees/*.yml`（Story 001）+ `perf-labels.json`（Story 002）

## 相關 commits
- `54d1af2` perf v5.1 Phase 2：三軸 dashboard 重構
- `ad57679` perf-dashboard: 個人頁 issue 列表加超連結
- `ccfe930` ci: Performance Dashboard 加 push trigger
- `168b481` 更新資料產生器：輸出符合 Dashboard 設計 schema
- `15da6ec` `ce8c23d` `c0a75ae` 前端 page1/2/3
- `6620a3e` 前端 app.js
- `397690b` 前端 style.css
- `3c7e26d` Dashboard workflow：加入前端檔案部署
- `7e5ec6b` Performance Dashboard workflow（每日自動 + issue 觸發）
- `b7d1c9f` Dashboard 資料產生器

## 備註
- 前端是純 vanilla HTML/CSS/JS，不引入 framework，避免 build pipeline
- Dashboard URL 走 GitHub Pages 預設路徑（gh-pages 分支根目錄）
- `data.json` 是契約——前端與資料產生器透過它解耦，改任一邊都要對齊 schema
- 月份 label 目前 hard-code 為 `["11月","12月","1月","2月","3月","4月"]`，2026/05 起需更新或改為動態產生
