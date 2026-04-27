# Story 003 — AI 自動標註，降低主管打 label 成本

## User Story
- **As** 部門主管
- **I want** issue 關閉／重開時，AI 自動讀內容、comments、關聯 PR、milestone，建議該打哪些 perf label
- **So that** 我不用人工巡所有 repo；客觀可判定的事件（milestone-missed、untested-delivery、surprise-delay）不會被遺漏；主管時間留給綠旗加分這類需主觀判斷的事

## 成功指標
- Issue close 後幾分鐘內，符合 `auto: true` 規則的 perf label 被自動打上
- AI 只動 `auto: true` 的 label，綠旗（`requires_confirm: true`）一律不自動加
- 跨 repo 自動執行（除 `.github` repo 本身）
- AI 判斷的依據（issue body / comments / PR / milestone）有完整 context，不只看標題
- Reopen 事件能正確處理（移除原本錯誤的 label / 重新評估）

## 涵蓋 Features
- [x] performance-auto-label.yml workflow — commit `024e8f3`
- [x] auto-label.py（GitHub Models gpt-4o + 抓 PR / milestone / comments） — commit `2a29711`
- [x] AI Collab CI lint（v5.1 Phase 1 一部分） — commit `fe52365`
- [x] reopen 事件處理（v5.1 Phase 2） — commit `54d1af2`

## 相關既有功能
- `.github/workflows/performance-auto-label.yml`
- `.github/workflows/ai-collab-lint.yml`
- `performance/scripts/auto-label.py`
- 讀 `perf-labels.json`（Story 002）作為 prompt 規則來源

## 相關 commits
- `54d1af2` perf v5.1 Phase 2：三軸 dashboard 重構 + cron workflows + reopen 事件處理
- `fe52365` perf v5.1 Phase 1：三軸架構 label / prompt / AI Collab CI lint
- `2a29711` 新增 auto-label.py：GitHub Copilot 分析 issue 內容自動標記績效標籤
- `024e8f3` 新增 Performance Auto Label：issue close 時 AI 自動判斷並打 perf label

## 備註
- 模型：`openai/gpt-4o` via GitHub Models（不額外付費，吃 GitHub Models 額度）
- 認證走 `PERF_TOKEN`（PAT），需要組織內 repo 的 `issues: write` 權限
- AI 判錯時主管可直接在 issue 上手動移除 label——下次 reopen→close 時 AI 會重新評估
- Body / comments 各限制 3000 字，避免 token 爆炸
