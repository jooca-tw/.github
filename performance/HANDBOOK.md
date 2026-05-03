# 績效考核制度手冊（HANDBOOK）

> 本文件為 O 部門員工績效考核的**權威說明**。Label 定義以 `performance/perf-labels.json` 為準（程式邏輯讀取的單一來源），本手冊負責補上**判定準則、實例、邊界情境**。
>
> 版本：對應 perf-labels v5.3（2026-04 上線）

---

## 1. 總則

### 1.1 三軸架構

v5.1 後績效採三軸計分（取代早期 O1-O5 五維度命名，`README.md` 的 5 維度為對外口語版本）：

| 軸 | 代碼 | 對應原維度 | 著重 |
|---|---|---|---|
| 軸 1 — AI 導入 | `axis1-ai-adoption` | O4 技術成長 | 是否在工作流引入 AI、產出共用資產 |
| 軸 2 — 如期 | `axis2-on-time` | O2 時程管理 | Milestone、變更管理、回應速度 |
| 軸 3 — 品質 | `axis3-quality` | O1 程式碼品質 | Bug、回滾、客戶端問題 |
| 一般綠旗 | `general` | O3/O5 加分項 | 跨軸加分（研究、危機、補位） |

### 1.2 角色（role）

| 角色 | 說明 |
|---|---|
| `rd` | 研發工程師，著重軸 3 品質、軸 1 AI 導入 |
| `pm` | 專案經理，著重軸 2 如期、變更管理 |
| `shared-pm-rd` | PM/RD 連坐（如 milestone-missed） |
| `all` | 全員適用 |

### 1.3 Label 類型（type）

| Type | 意義 | 是否計分 |
|---|---|---|
| `deduction` | 紅旗扣分 | ✅ 扣 |
| `bonus` | 綠旗加分 | ✅ 加（多數需主管確認） |
| `info` | 資訊紀錄 | ❌ 0 分 |
| `warning` | 警示，列月報 | ❌ 0 分 |
| `meta` | 標記用（如 tier、豁免、觸發條件） | ❌ |

### 1.4 計分原則

- **AI 自動標 (`auto: true`)**：紅旗為主，發生即計分
- **主管確認 (`requires_confirm: true`)**：綠旗一律須確認，避免被刷
- **月度上限 (`monthly_cap`)**：避免單一行為灌水（如 rework-credit +1/件、上限 +5）
- **豁免 (meta labels)**：用標記 label 抵銷誤判（如 `intentional-rollback` 豁免 `quality-rollback`）

---

## 2. RD vs PM 評估維度差異

### 2.1 RD（junior-rd / senior-rd-a / senior-rd-b）

**主軸**：軸 3 品質、軸 1 AI 導入

| 直接適用 label | 分數 |
|---|---|
| `perf:hidden-bug` | -5 |
| `perf:untested-delivery` | -3（註：定義在舊版 README，新版已收斂到 quality-rollback 體系） |
| `perf:quality-rollback` | -3 |
| `perf:customer-bug` | -3 |
| `perf:rework-credit` | +1/件，月上限 +5 |
| `perf:ai-zero`（警示） | 0 |
| `perf:milestone-missed`（連坐） | -2 |
| `perf:review-lag`（PR ≥ 48h 未 review） | -1/件，月上限 -5 |

**RD 不適用**：所有 `scope-creep-*`、`customer-late-reply`、`spec-not-frozen` 等 PM 變更管理類。

### 2.2 PM

**主軸**：軸 2 如期、變更管理

| 直接適用 label | 分數 |
|---|---|
| `perf:milestone-missed` | -5（主責） |
| `perf:customer-late-reply` | -2 |
| `perf:scope-creep-external-handled` | 0（紀錄） |
| `perf:scope-creep-external-unmanaged` | -3 |
| `perf:scope-creep-internal` | -2 |
| `perf:spec-not-frozen` | -3 |
| `perf:spec-mismatch` 連坐 | -2 |
| `perf:change-management-good` | +5～+10 |

**PM 不適用**：`hidden-bug`、`customer-bug`、`quality-rollback` 等品質 label。

### 2.3 全員適用

`surprise-delay`、`review-lag`、`ai-zero` 警示，及所有綠旗（`tech-research` / `crisis-handling` / `team-backup` / `tier-jump` / `ai-contribution`）。

---

## 3. Label 詳解

### 3.1 紅旗（扣分類）

#### `perf:hidden-bug` − 5 ｜ RD ｜ 軸 3 ｜ 人工
- **定義**：明知有問題卻偷偷上線，未通報。
- **判定**：commit / PR 留下「明知 fail 仍 merge」「跳過 reviewer 警告」「事後私下修補」證據。
- **實例**：明知 race condition 但未開 issue，等線上炸了才補。
- **不算**：合理範圍內未察覺的 bug（屬 `customer-bug` 或 `quality-rollback`）。
- **為何人工**：意圖判斷需主管/同儕脈絡，AI 易誤判。

#### `perf:milestone-missed` − 5 PM / − 2 RD ｜ 軸 2 ｜ AI 自動
- **定義**：milestone deadline 已過，issue 未關閉。
- **PM 主責 −5**；同 milestone 的 RD **連坐 −2**。
- **RD 免責情境**：
  1. 該 milestone 有 `scope-creep-external-*` / `scope-creep-internal`（責歸 PM 變更管理）
  2. PM 在中後段才改 deadline（時程被壓縮）
  3. 後期 reassign（接手不到 50% 時間）

#### `perf:surprise-delay` − 5 ｜ All ｜ 軸 2 ｜ AI 自動
- **定義**：deadline 前 ≤ 24h 才首次預警。
- **判定**：AI 比對 issue/comments/milestone 進度更新時點。
- **避免方式**：deadline 前 ≥ 3 天就在 issue 留進度說明。

#### `perf:customer-late-reply` − 2 ｜ PM ｜ 軸 2 ｜ AI 自動
- **定義**：外部（客戶）在 issue 留 comment 後 > 1 小時未回。
- **計算**：工作時間內（避免半夜誤判 — 由 auto-label.py prompt 控制）。

#### `perf:scope-creep-external-handled` 0 ｜ PM ｜ 軸 2 ｜ AI 自動
- **定義**：客戶插單 + PM 已開 `perf:milestone-renegotiated` 重議 milestone。
- **不扣分**，僅紀錄。月度若達 ≥ 3 次 + 命中率 ≥ 80%，可申請 `change-management-good` 加分。

#### `perf:scope-creep-external-unmanaged` − 3 ｜ PM ｜ 軸 2 ｜ AI 自動
- **定義**：客戶插單但 PM 未重議 milestone（變更管理失職）。
- **重點**：扣的不是「插單發生」，而是「沒做變更管理」。

#### `perf:scope-creep-internal` − 2 ｜ PM ｜ 軸 2 ｜ AI 自動
- **定義**：milestone 進行中，內部（非客戶）新增需求。
- **判定**：issue/PR 在 milestone 啟動後加入，且無客戶來信佐證。

#### `perf:scope-creep` − 2 ｜ PM ｜ ⚠️ Deprecated v5.2
- 改用上面三細項。Dashboard 仍會計分但會標 deprecated banner。

#### `perf:spec-not-frozen` − 3 ｜ PM ｜ 軸 2 ｜ AI 自動
- **定義**：milestone 開始 7 天後仍無 `perf:spec-frozen` + 已發生 ≥ 2 次 `requirement-change`。
- **語意**：規格遲遲未鎖定，PM 規格釐清失職。
- **避免方式**：milestone kick-off 後盡早打 `perf:spec-frozen`。

#### `perf:quality-rollback` − 3 ｜ RD（原 closer）｜ 軸 3 ｜ AI 自動
- **定義**：issue 結案後 30 天內被 reopen。
- **歸責**：原 closer。可申訴轉移（如接手者引入新 bug）。
- **免責 meta**：`perf:scope-change`（需求變了）、`perf:intentional-rollback`（負責任退版，24h 內加）。

#### `perf:customer-bug` − 3 ｜ RD ｜ 軸 3 ｜ AI 自動
- **定義**：客戶端發現的 bug。
- **觸發**：issue 帶 `perf:customer-reported` 或客戶 GitHub 帳號留言報 bug。
- **免責 meta**：`perf:not-a-bug`（誤報/環境）、`perf:spec-mismatch`（規格理解差異，PM 連坐 −2）。

#### `perf:review-lag` − 1/件 ｜ All ｜ 軸 2 ｜ AI 自動
- **定義**：PR 開立 ≥ 48h 仍無 review。
- **歸責**：被指定的 reviewer。
- **月度上限 −5**。

### 3.2 綠旗（加分類，多數需主管確認）

#### `perf:rework-credit` + 1/件，月上限 + 5 ｜ RD ｜ 軸 2 ｜ AI 自動
- **定義**：上游打 `perf:requirement-change` 時，自動觸發給原 RD。
- **語意**：需求變更不是 RD 的錯，補償重做成本。
- **唯一不需主管確認的綠旗**（自動觸發）。

#### `perf:change-management-good` + 5～+ 10 ｜ PM ｜ 軸 2 ｜ 主管確認
- **觸發條件**：月內 ≥ 3 次客戶插單 + **全部** `milestone-renegotiated` + 命中率 ≥ 80%。
- **語意**：高擾動環境下仍管理得宜的 PM。

#### `perf:ai-contribution` + 5～+ 10 ｜ All ｜ 軸 1 ｜ 主管確認
- **定義**：產出共用 AI skill / template / agent / 內訓教材。
- **判定**：產出物在 org 內被他人使用。

#### `perf:tech-research` + 5～+ 20 ｜ All ｜ 主管確認
- **三檔**：
  - +5～8：概念驗證（POC）
  - +10～15：決策指引（影響團隊技術選型）
  - +16～20：落地變現（產品化、節省成本）

#### `perf:crisis-handling` + 5～+ 10 ｜ All ｜ 主管確認
- 線上事故 / 地獄模式（爆量插單、客戶炸鍋）下表現佳。

#### `perf:team-backup` + 3～+ 5 ｜ All ｜ 主管確認
- 主動介入同事卡關，非自身工單。

#### `perf:tier-jump` + 5～+ 8 ｜ All ｜ 軸 2 ｜ AI 自動 + 主管確認
- 承接高於職級難度的專案（看 `perf:tier-N` label）。
- AI 偵測候選，主管確認加成幅度。

### 3.3 警示與 Meta

#### `perf:ai-zero` 0 ｜ 警示 ｜ All ｜ 軸 1
- 當月個人 PR 無 AI Collaboration 段落達標。**不扣分**，但列月報。
- 連續 N 月可作為主管面談依據。

#### Meta（標記用，不計分）
| Label | 用途 |
|---|---|
| `perf:spec-frozen` | PM 鎖定規格，防止 spec-not-frozen 觸發 |
| `perf:milestone-renegotiated` | PM 重議 deadline，觸發 scope-creep-external-handled |
| `perf:intentional-rollback` | 負責任退版（24h 內加），豁免 quality-rollback |
| `perf:scope-change` | reopen 因需求變更，豁免 quality-rollback |
| `perf:customer-reported` | 客戶反映，觸發 customer-bug 判定 |
| `perf:not-a-bug` | 客戶誤報，豁免 customer-bug |
| `perf:spec-mismatch` | 規格理解差異，PM 連坐 −2，豁免 RD customer-bug |
| `perf:requirement-change` | 規格已交付一次後再改，純紀錄並觸發 rework-credit |

#### Tier（專案難度）
| Label | 難度 | 典型情境 |
|---|---|---|
| `perf:tier-1` | 最簡單 | 文案改動、設定調整 |
| `perf:tier-2` | 簡單 | 既有功能小改 |
| `perf:tier-3` | 標準 | 一般功能開發 |
| `perf:tier-4` | 困難 | 跨系統整合、效能優化 |
| `perf:tier-5` | 最困難 | 新架構、技術突破 |

Tier 不直接計分，但決定 `tier-jump` 加成幅度與綠旗判斷脈絡。

---

## 4. 灰色地帶處理

### 4.1 客戶插單（v5.2 三級拆解）

| 情境 | Label | 分數 |
|---|---|---|
| 客戶插單 + PM 重議 milestone | `scope-creep-external-handled` | 0 |
| 客戶插單 + PM 沒重議 | `scope-creep-external-unmanaged` | −3 |
| 內部加項（非客戶） | `scope-creep-internal` | −2 |

**原則**：插單本身不是錯，**沒做變更管理才是**。

### 4.2 需求變更（v5.3 機制）

```
需求改了 → 打 perf:requirement-change（純紀錄）
            ↓
        自動觸發 perf:rework-credit 給原 RD（+1/件，補償重做）
            ↓
若 7 天內無 spec-frozen + ≥ 2 次 requirement-change
            ↓
        打 perf:spec-not-frozen（PM −3）
```

### 4.3 品質爭議申訴

- `quality-rollback` / `customer-bug` 可由 RD 申訴
- 主管打 `intentional-rollback` / `not-a-bug` / `spec-mismatch` 之一豁免
- 申訴期：label 出現後 7 天內

---

## 5. 加分申請流程

1. RD/PM 自評，於對應 issue 建議綠旗類型
2. 主管於 issue 補上對應 label（含分數，如 `perf:tech-research +12`）
3. Dashboard 下次跑會納入

> 綠旗無法「自我加分」，一律由主管或上級主管確認。

---

## 6. TODO（待補）

- [ ] `perf:untested-delivery` 在 v5.3 是否仍存在？需與 perf-labels.json 對齊（目前 JSON 沒有此 label，README 仍列）
- [ ] 季度 PM Review 三層架構與 issue template 對應流程詳述（連結 `.github/ISSUE_TEMPLATE/quarterly-pm-review.md`）
- [ ] 軸 1 AI 導入的判定門檻（PR 中 AI Collaboration 段落格式規範）
- [ ] 申訴流程的正式 issue template

---

## 7. 相關文件

- `performance/perf-labels.json` — 程式讀取的 label 定義（**單一真實來源**）
- `performance/sync-perf-labels.sh` — 同步 label 到 org 全 repo
- `README.md` — 系統架構概覽
- `stories/002-perf-events-on-issues/STORY.md` — label 演進歷史與決策
- `stories/004-performance-dashboard/STORY.md` — Dashboard 計分實作
- `.github/ISSUE_TEMPLATE/quarterly-pm-review.md` — PM 季度 review template
- `.github/ISSUE_TEMPLATE/-kr--.md` — 週報 KR template
