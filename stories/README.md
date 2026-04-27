# Stories — 雙層需求文件

本目錄是本 repo 的 **需求／規格層**。Code 是實作真相，Stories 是「為什麼存在這些 code」的真相。

## 索引

| # | Story | 狀態 | 說明 |
|---|---|---|---|
| 001 | [員工人事檔案的單一真實來源](001-employee-source-of-truth/STORY.md) | ✅ 已上線 | 員工 YAML + schema 驗證 |
| 002 | [以 GitHub Issue 作為績效事件的事實基礎](002-perf-events-on-issues/STORY.md) | ✅ 已上線 | perf:* labels + 同步機制 |
| 003 | [AI 自動標註，降低主管打 label 成本](003-ai-auto-labeling/STORY.md) | ✅ 已上線 | issue close → AI → label |
| 004 | [全員績效即時可視化儀表板](004-performance-dashboard/STORY.md) | ✅ 已上線 | 跨 repo 彙整 + gh-pages |
| 005 | [主動預警與週期性績效彙整](005-proactive-alerts-and-cycles/STORY.md) | ✅ 已上線 | deadline / review-lag / 月報 / 季度 |
| 006 | [員工以週報結構化追蹤 KR 進度](006-kr-weekly-report/STORY.md) | ✅ 已上線 | KR issue template |

狀態：`📝 草案` / `🚧 進行中` / `✅ 已上線` / `🗄 封存`

## 目錄結構

```
stories/
├── README.md                       # 本檔，索引 + 流程
├── _templates/                     # 寫新 story / feature 用的模板
│   ├── STORY.md
│   ├── SPEC.md
│   ├── plan.md
│   └── todo.md
└── NNN-slug/                       # 一個 Story
    ├── STORY.md                    # User story、成功指標、涵蓋 features
    └── features/
        └── <feature-slug>/         # 實作這個 Story 的某個切片
            ├── SPEC.md             # 需求與驗收
            ├── plan.md             # 技術方案
            └── todo.md             # 任務清單
```

**Story** = 業務語言、跨多個 feature、長壽命。
**Feature** = 一次具體的開發工作、可獨立 spec → plan → build → 合併。

## 新需求流程

```
新需求
  ↓
歸屬到既有 Story（看 stories/README.md 索引）
  ↓ 找不到 → 新開 Story（複製 _templates/STORY.md）
  ↓
建 features/<slug>/ 目錄
  ↓
/spec   → 寫 SPEC.md       （觸發 skill: spec-driven-development）
  ↓
/plan   → 寫 plan.md        （觸發 skill: planning-and-task-breakdown）
  ↓
/build  → 跑 todo.md         （觸發 skill: incremental-implementation + test-driven-development）
  ↓
合併 → 在 STORY.md 把該 feature 打勾、附 commit hash
```

## Skill 對照

| 流程階段 | 推薦 skill | 用途 |
|---|---|---|
| 寫 SPEC.md | `spec-driven-development` | 需求釐清，防止跳過去寫 code |
| 寫 plan.md | `planning-and-task-breakdown` | 切片、估範圍 |
| 寫 plan 的 API 段 | `api-and-interface-design` | 介面設計 |
| 跑 todo.md | `incremental-implementation` | 一次一刀、可驗證 |
| 改既有邏輯 | `test-driven-development` | 先測再改 |
| 卡住 | `debugging-and-error-recovery` | 系統性 root cause |
| 合併前 | `code-review-and-quality` | 多軸 review |

## 設計原則

1. **Code 為真相、Stories 為動機**——既有功能不補 SPEC.md，只有新需求走 spec 流程。
2. **STORY.md 持續活著**——每次 ship 一個 feature 就回來打勾、附 commit hash，讓未來能從 story 反查實作軌跡。
3. **Feature 切到「一次合併」就完成**——切太大就拆兩個 feature，不要在一個 todo.md 裡掛三個月。
4. **Story 不爆量**——超過 8 個就是切太細，往上收斂；少於 3 個通常是切太粗。
