# .github

Hyweb O 部門（數位智能整合事業處）共用設定 repo，承載 **員工績效考核系統**：以 GitHub Issues + Labels 作為單一資料來源，透過 GitHub Actions 自動評分、AI 標註，並發佈靜態 Dashboard 到 GitHub Pages。

## 主要邏輯（一句話版）

**Issue 是事件、Label 是分數、Action 是計分器、Dashboard 是儀表**。員工日常工作本來就在 GitHub 開 issue / PR，主管或 AI 在 issue 上補 `perf:*` label（紅旗扣分 / 綠旗加分 / tier 標難度），cron 每日跨 org 彙整 → 部署 Dashboard。**不另開系統、不另填表**。

## 主要 Story（雙層需求結構）

| # | 主題 | 核心檔案 |
|---|---|---|
| [001](stories/001-employee-source-of-truth/STORY.md) | 員工人事檔案的單一真實來源 | `performance/employees/*.yml` + `validate.py` |
| [002](stories/002-perf-events-on-issues/STORY.md) | 以 GitHub Issue 作為績效事件的事實基礎 | `perf-labels.json` + `sync-perf-labels.sh` |
| [003](stories/003-ai-auto-labeling/STORY.md) | AI 自動標註，降低主管打 label 成本 | `auto-label.py` + `performance-auto-label.yml` |
| [004](stories/004-performance-dashboard/STORY.md) | 全員績效即時可視化儀表板 | `generate-dashboard-data.py` + `dashboard/` |
| [005](stories/005-proactive-alerts-and-cycles/STORY.md) | 主動預警與週期性績效彙整 | `alerts` / 季度 PM Review template |
| [006](stories/006-kr-weekly-report/STORY.md) | 員工以週報結構化追蹤 KR 進度 | `[KR].md` issue template |

新需求流程與 skill 對照見 [`stories/README.md`](stories/README.md)。

## 大型版本紀錄（Changelog）

> ⚠️ **目前仍在試營運階段，尚未正式上線**。版本號維持 v0.x，待制度與 dashboard 穩定運行一段時間後才會升至 v1.0。

| 日期 | 版本 | 摘要 |
|---|---|---|
| 2026-04-14 | v0.1 | 員工 YAML schema 驗證 workflow 上線（CI 把關人事資料）|
| 2026-04-16 | v0.2 | schema 加 `projects` 欄位 + 全員員工檔同步 |
| 2026-04-18 | v0.3 | **MVP 雛形**：16 個 perf label、sync 腳本、Dashboard 三頁、Auto-label workflow（GitHub Models / gpt-4o）全數開通 |
| 2026-04-27 | v0.4 | **三軸架構**取代 5 維度（AI 導入 / 如期 / 品質）；dashboard 重構、cron workflows、reopen 事件處理；AI Collab CI lint |
| 2026-04-27 | v0.5 | **客戶插單變更管理機制**：`scope-creep` 拆三級（external-handled / external-unmanaged / internal）+ `change-management-good` 加分機制 |
| 2026-04-27 | v0.6 | **需求變更機制 + PM 績效三層架構**：`requirement-change` / `rework-credit` / `spec-frozen` / `spec-not-frozen`；季度 PM Review issue template；dashboard 視覺化 6 項補強 |
| 2026-05-03 | v0.6.1 | 新增 [`performance/HANDBOOK.md`](performance/HANDBOOK.md)（label 詳解、RD vs PM 維度差異、灰色地帶、申訴流程） |

> 大型更動（label 體系變動、計分邏輯、新增軸）請在此追加一列；commit hash 可在 `git log` 查到，不重複列。
> 正式上線（v1.0）的條件：制度試跑 ≥ 1 季 + 員工/主管回饋收斂 + 申訴流程驗證過。

## 系統概念

考核採三軸架構（v5.1 後）：

| 軸 | 代碼 | 對應原 5 維度（口語版） |
|---|---|---|
| 軸 1 — AI 導入 | `axis1-ai-adoption` | O4 技術成長 |
| 軸 2 — 如期 | `axis2-on-time` | O2 時程管理 |
| 軸 3 — 品質 | `axis3-quality` | O1 程式碼品質 |
| 一般綠旗 | `general` | O3 團隊協作 / O5 客戶滿意度 |

員工資料以 YAML 集中管理（`performance/employees/*.yml`），Issue 上的 `perf:*` label 即為扣分／加分事件，dashboard 跨 repo 彙整後計分。

> **完整制度說明（label 詳解、RD vs PM 維度差異、灰色地帶、申訴流程）**：見 [`performance/HANDBOOK.md`](performance/HANDBOOK.md)

> 部門主管不納入評分（`Hyweb-JayKao.yml` 僅作 schema 範本）。

## 目錄結構

```
.
├── .github/
│   ├── workflows/
│   │   ├── performance-auto-label.yml   # Issue close/reopen 觸發 AI 自動打 perf label
│   │   ├── performance-dashboard.yml    # 每日重算資料 + 部署 Dashboard 到 gh-pages
│   │   └── validate-employees.yml       # PR 驗證員工 YAML schema
│   └── ISSUE_TEMPLATE/
│       └── [KR].md                      # 週報模板（週一～週五工單記錄）
└── performance/
    ├── perf-labels.json                 # 16 個 perf label 集中定義
    ├── sync-perf-labels.sh              # 將 labels 同步到組織所有 repo
    ├── validate.py                      # 員工 YAML JSON Schema + GitHub 帳號驗證
    ├── employees/                       # 11 位員工檔（檔名 == github_login.yml）
    ├── scripts/
    │   ├── auto-label.py                # GitHub Models (gpt-4o) 分析 issue → 打 label
    │   └── generate-dashboard-data.py   # 跨 repo 彙整 perf issues → data.json
    └── dashboard/                       # 靜態前端（vanilla HTML/CSS/JS）
        ├── page1.html                   # 部門總覽
        ├── page2.html                   # 個人頁
        ├── page3.html                   # 警示頁
        ├── style.css
        └── app.js
```

## 績效標籤（perf-labels.json）

> 詳細定義（含判定準則、實例、免責情境）見 [`performance/HANDBOOK.md`](performance/HANDBOOK.md)。本節僅為快速摘要。

下表為核心 label，分三類：

### 紅旗（扣分，6 項）
| Label | 分數 | 維度 | 角色 | AI 自動 |
|-------|-----:|------|------|:------:|
| `perf:hidden-bug` | -5 | O1 | RD | ❌ 需人工 |
| `perf:milestone-missed` | -5 | O2 | PM | ✅ |
| `perf:surprise-delay` | -5 | O2 | All | ✅ |
| `perf:untested-delivery` | -3 | O1 | RD | ✅ |
| `perf:customer-late-reply` | -2 | O3 | PM | ✅ |
| `perf:scope-creep` | -2 | O2 | PM | ✅ |

### 綠旗（加分，5 項，皆需主管確認）
| Label | 分數 | 維度 |
|-------|------|------|
| `perf:tech-research` | +5～20 | O4 |
| `perf:ai-app` | +5～20 | O5 |
| `perf:crisis-handling` | +5～10 | O1/O2 |
| `perf:team-backup` | +3～5 | O3 |
| `perf:tier-jump` | +5～8 | O2 |

### Tier（meta，5 項）
`perf:tier-1` ～ `perf:tier-5`：標示專案難度，不直接計分。

執行 `performance/sync-perf-labels.sh` 把這份定義同步到組織各 repo。

## 員工 YAML Schema（validate.py）

必填：`employee`、`github_login`、`real_name`、`email`、`role`、`joined`、`active`，外加 `manager` 或 `manager_name` 至少一項。

額外規則：
- 檔名必須等於 `{github_login}.yml`
- `role` ∈ {`junior-rd`, `senior-rd-a`, `senior-rd-b`, `pm`}
- `active: false` 時必填 `left_at`
- `manager` 必須指向另一份檔的 `github_login`
- 提供 `GITHUB_TOKEN` 時會驗證 `github_login` 真實存在

`validate-employees.yml` 在 PR 修改 `performance/employees/**.yml` 或 `validate.py` 時觸發。

## 三條 Workflow

### 1. performance-auto-label.yml — Issue → AI → Label
- **觸發**：組織內任一 repo 的 issue `closed` / `reopened`（排除 `.github` repo 本身）
- **流程**：
  1. Checkout `jooca-tw/.github`（用 `PERF_TOKEN`）
  2. 透過 `gh api` 蒐集 issue body / comments / 關聯 PR / milestone 資訊
  3. 呼叫 GitHub Models (`openai/gpt-4o`) 比對 `perf-labels.json` 中 `auto: true` 的規則
  4. 為原 issue 補上對應的 perf label

### 2. performance-dashboard.yml — Dashboard 部署
- **觸發**：每日 00:00 UTC cron / issue label 變動 / 手動 dispatch
- **流程**：
  1. `generate-dashboard-data.py` 用 `PERF_TOKEN` 跨整個 `jooca-tw` org 搜尋帶 `perf:*` 的 issues
  2. 對應 `employees/*.yml` 計分，依 5 維度彙整出 `stats / members / alerts / alert_summary`
  3. 產出 `dashboard-out/data.json`，連同 `dashboard/*.{html,css,js}` 一起 publish 到 **gh-pages 分支**

### 3. validate-employees.yml — Schema 驗證
PR / push 修改員工 YAML 時跑 `validate.py`，失敗會以 GitHub Actions annotation 標出問題行。

## 週報模板（[KR].md）

固定格式 issue：週一～週五，每天列出工單並填：

```
- [ ] `預估：X hrs, 完成度：N%`｜`實際：Y hrs`｜#單號
```

每天有「未達標原因」備註欄。供主管追蹤 KR 進度，亦是後續 perf label 的判斷依據。

## 必要 Secrets

| Secret | 用途 |
|--------|------|
| `PERF_TOKEN` | PAT，跨 repo 搜尋 issues / 寫入 label / checkout `.github` |
| `GITHUB_TOKEN` | 內建，部署 gh-pages 用 |

## 常見作業

**新增員工**
1. `performance/employees/Hyweb-{Name}.yml`（檔名與 `github_login` 一致）
2. 開 PR → `validate-employees` workflow 自動檢查
3. 合併後下次 dashboard 跑就會納入

**新增 / 調整 perf label**
1. 編輯 `performance/perf-labels.json`
2. 跑 `performance/sync-perf-labels.sh` 同步到各 repo
3. 若是 `auto: true`，AI 會在下次 issue close 時開始套用

**Dashboard 預覽**
合併到 `main` 後等 workflow 部署，到 `https://jooca-tw.github.io/.github/page1.html`（或對應 GitHub Pages URL）查看。
