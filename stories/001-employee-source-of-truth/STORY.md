# Story 001 — 員工人事檔案的單一真實來源

## User Story
- **As** 部門主管 / HR
- **I want** 把每位成員的角色、主管、入職日、所屬專案以版本控管的 YAML 集中維護，並在 PR 時自動驗證
- **So that** dashboard 與評分機制不會用到髒資料、人員異動有 audit trail、避免「Excel 一份、Slack 一份、口頭一份」的漂移

## 成功指標
- 所有員工資料在 `performance/employees/*.yml`，一人一檔，檔名 == `github_login.yml`
- PR 修改員工檔即跑 schema 驗證（角色 enum、email 格式、manager 交叉檢查、GitHub 帳號實存）
- 離職員工 `active: false` 且必填 `left_at`，不從目錄移除（保留歷史）
- `validate.py` 失敗時以 GitHub Actions annotation 標出問題行

## 涵蓋 Features
- [x] 員工 YAML schema 與驗證腳本 — commit `2a29711` 之前已建立
- [x] schema 加入 `projects` 欄位 — commit `ff29631`
- [x] schema 加入 `system_type` enum — commit `64d08c2`
- [x] 11 位員工資料同步上線 — commits `15eb950` `326598f` `287b966` `837c76e` `449354c`

## 相關既有功能
- `performance/employees/*.yml`（11 份）
- `performance/validate.py`（JSON Schema + GitHub user check）
- `.github/workflows/validate-employees.yml`（PR/push 觸發）

## 相關 commits
- `64d08c2` fix(validate): schema 加 system_type enum（legacy/new-feature/internal-tooling/general）
- `ff29631` feat: schema 加入 projects 欄位
- `449354c` `837c76e` `287b966` `326598f` `15eb950` sync: 員工專案分配

## 備註
- 部門主管（Jay）依制度第 1 節**不納入評分**，YAML 僅作為 schema 範本
- `manager` 與 `manager_name` 擇一即可（外部主管沒 GitHub 帳號時用後者）
- 後續若加新欄位，須同步更新 `validate.py` 的 `SCHEMA` 與 `generate-dashboard-data.py` 的讀取邏輯
