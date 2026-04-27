# Story 006 — 員工以週報結構化追蹤 KR 進度

## User Story
- **As** O 部門員工
- **I want** 一個固定格式的週報 issue 模板，每天記錄工單的預估時數／完成度／實際時數／單號與未達標原因
- **So that** 我跟主管有共同語言追蹤 KR 進度；後續評分也有原始素材可回查；自我反思「為什麼預估失準」有持續紀錄

## 成功指標
- 員工可以在任何 repo 用 GitHub issue template 一鍵開週報
- 模板涵蓋週一至週五，每日有「工單」與「備註（未達標原因）」兩段
- 每筆工單格式統一：`預估 hrs / 完成度 % / 實際 hrs / #單號`
- 週報本身是 GitHub issue，所以也能被 perf:* label 與 dashboard 統計（與 Story 002/004 串接）

## 涵蓋 Features
- [x] [KR] issue template — 已上線

## 相關既有功能
- `.github/ISSUE_TEMPLATE/-kr--.md`

## 相關 commits
- （初始模板，commit hash 早於 30 commits 視窗）

## 備註
- 員工視角的 story，與其他 5 個（主管視角）職能不同
- 模板採 markdown checkbox + inline code 格式，方便後續被 AI 或腳本解析
- 「備註」欄位很關鍵：是 surprise-delay / scope-creep 等紅旗 label 在週報層次的早期信號
- 後續若要做「週報自動彙整成月報」或「未達標原因 AI 分類」，可從這裡延伸新的 feature
