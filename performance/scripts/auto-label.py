#!/usr/bin/env python3
"""
績效考核自動標籤
Issue close 時，用 GitHub Copilot (GitHub Models) 分析 issue 內容，
自動判斷並打上 perf: label。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml
from openai import OpenAI

# ── Config ──

PERF_LABELS_PATH = Path("performance/perf-labels.json")
EMPLOYEES_DIR = Path("performance/employees")
MODEL = "openai/gpt-4o"  # GitHub Models 提供的模型


def get_issue_details() -> dict:
    """從環境變數和 GitHub API 取得 issue 完整資訊。"""
    repo = os.environ["ISSUE_REPO"]
    number = os.environ["ISSUE_NUMBER"]
    assignees = os.environ.get("ISSUE_ASSIGNEES", "")
    existing_labels = os.environ.get("ISSUE_LABELS", "")

    # 取得 issue body
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{number}", "--jq", ".body"],
        capture_output=True, text=True, timeout=30,
    )
    body = result.stdout.strip() if result.returncode == 0 else ""

    # 取得 comments
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{number}/comments",
         "--jq", '[.[] | {user: .user.login, body: .body}] | tostring'],
        capture_output=True, text=True, timeout=30,
    )
    comments = result.stdout.strip() if result.returncode == 0 else "[]"

    # 取得關聯 PR 的檔案變更（檢查有無 test）
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{number}/timeline",
         "--jq", '[.[] | select(.event=="cross-referenced") | .source.issue.pull_request.html_url // empty] | tostring'],
        capture_output=True, text=True, timeout=30,
    )
    pr_urls = result.stdout.strip() if result.returncode == 0 else "[]"

    # 取得 milestone 資訊
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{number}",
         "--jq", '{milestone_title: .milestone.title, milestone_due: .milestone.due_on, closed_at: .closed_at}'],
        capture_output=True, text=True, timeout=30,
    )
    milestone_info = result.stdout.strip() if result.returncode == 0 else "{}"

    return {
        "repo": repo,
        "number": number,
        "title": os.environ.get("ISSUE_TITLE", ""),
        "body": body[:3000],  # 限制長度
        "assignees": assignees,
        "existing_labels": existing_labels,
        "comments": comments[:3000],
        "pr_urls": pr_urls,
        "milestone_info": milestone_info,
    }


def load_perf_labels() -> list[dict]:
    if not PERF_LABELS_PATH.exists():
        return []
    with open(PERF_LABELS_PATH) as f:
        return json.load(f)


def load_employee_role(login: str) -> str:
    """取得員工角色。"""
    for f in EMPLOYEES_DIR.glob("*.yml"):
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if data and data.get("github_login") == login:
            return data.get("role", "unknown")
    return "unknown"


def build_prompt(issue: dict, labels: list[dict], employee_roles: dict) -> str:
    """建構給 AI 的 prompt。"""

    labels_desc = "\n".join([
        f"- `{lb['name']}`: {lb['description']} (type: {lb['type']}, "
        f"score: {lb.get('score', lb.get('score_range', 'N/A'))})"
        for lb in labels if lb["type"] in ("deduction", "bonus")
    ])

    roles_desc = "\n".join([
        f"- {login}: {role}" for login, role in employee_roles.items()
    ])

    return f"""你是 O 部門的績效考核 AI 助手。請分析以下 GitHub Issue，判斷是否需要打上績效標籤。

## 可用的績效標籤

{labels_desc}

## Issue 指派的員工角色

{roles_desc}

## Issue 資訊

- **Repo**: {issue['repo']}
- **Issue #{issue['number']}**: {issue['title']}
- **已有標籤**: {issue['existing_labels']}
- **Milestone**: {issue['milestone_info']}
- **關聯 PR**: {issue['pr_urls']}

### Issue 內容
{issue['body'][:2000]}

### 留言紀錄
{issue['comments'][:1500]}

## 判斷規則（v5.1，2026-05-01 起算）

考核三軸：軸1 AI 導入 / 軸2 如期交付 / 軸3 品質。**個人考核只做紅燈（找異常），不做綠燈排序**。

1. **只標記有明確證據的事件**。不確定就不標。

2. **扣分標籤（紅旗）**：

   ### 軸 2 如期
   - issue 標題或留言提到「bug 被隱瞞」「上線後才發現」→ `perf:hidden-bug`
   - milestone 已過期 → `perf:milestone-missed`（PM -5 + RD 連帶 -2）
     - **RD 免責條件**（命中任一即只 PM 扣分）：issue 含 `perf:scope-creep` / PM 在 milestone ≥ 50% 工期才更新 deadline / RD 被重新 assign 距 deadline < 1.5x 預估工時
   - 從留言看出 deadline 前最後一刻才通知延遲 → `perf:surprise-delay`
   - 客戶留言後超過 1 小時未回覆 → `perf:customer-late-reply`（僅 PM）
   - milestone 進行中新增了這個 issue → `perf:scope-creep`（僅 PM）

   ### 軸 3 品質（v5.1 新增）
   - **issue 是 reopened 事件 + closed_at 與 reopened 時間差 ≤ 30 天** → `perf:quality-rollback`（-3 給原 closer）
     - **免責條件**：issue 含 `perf:scope-change` / `perf:intentional-rollback` label
   - **issue 含 `perf:customer-reported` label 或留言來自客戶 GitHub 帳號**（白名單 `performance/customer-accounts.json`） → `perf:customer-bug`（-3 給主責 RD）
     - **免責條件**：issue 含 `perf:not-a-bug` / `perf:spec-mismatch`（後者改 PM 連帶 -2）

   ### 已砍除
   - ❌ `perf:untested-delivery`：v5.1 砍除（process metric 不準），改用 quality-rollback 與 customer-bug

3. **加分標籤（綠旗）**：在留言中看到明確的正面貢獻時標記：

   ### 軸 1 AI 導入（v5.1 改版）
   - 產出共用 skill / template / agent / 內訓給團隊用 → `perf:ai-contribution`（+5~10，主管確認）
   - **已砍除**：`perf:ai-paired`（v3 行為軌）、`perf:ai-app`（v3 產出軌）→ 全併入 `perf:ai-contribution`

   ### 通用
   - 做了技術研究、PoC、產出評估報告 → `perf:tech-research`
   - 處理了緊急事故且表現良好 → `perf:crisis-handling`
   - 主動幫助同事解決卡關問題 → `perf:team-backup`

4. **注意角色適用性**：RD 的標籤不要標給 PM，反之亦然。
5. **已有的 perf: 標籤不要重複標記**。
6. **一般的 bug fix、feature 開發、日常任務不需要標記**——只標記特別好或特別差的事件。

## 回覆格式

回覆一個 JSON 物件，格式如下。如果沒有任何標籤需要標記，labels 陣列留空：

```json
{{
  "labels": [
    {{
      "name": "perf:label-name",
      "reason": "簡短說明為什麼標記這個標籤（一句話）"
    }}
  ],
  "summary": "一句話總結這個 issue 的績效影響"
}}
```

只回覆 JSON，不要其他文字。"""


def call_copilot(prompt: str) -> dict:
    """呼叫 GitHub Models API。"""
    client = OpenAI(
        base_url="https://models.github.ai/inference",
        api_key=os.environ["GITHUB_TOKEN"],
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是績效考核標籤判斷 AI。只回覆 JSON 格式。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
    )

    content = response.choices[0].message.content.strip()
    # 移除 markdown code block 如果有的話
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]

    return json.loads(content)


def apply_labels(issue: dict, result: dict):
    """將 AI 判斷的標籤打上 issue，並留 comment 說明。"""
    labels_to_add = result.get("labels", [])
    summary = result.get("summary", "")

    if not labels_to_add:
        print(f"No perf labels needed for #{issue['number']}")
        return

    existing = set(issue["existing_labels"].split(",")) if issue["existing_labels"] else set()
    new_labels = [lb for lb in labels_to_add if lb["name"] not in existing]

    if not new_labels:
        print(f"All suggested labels already exist on #{issue['number']}")
        return

    # 打上標籤
    label_names = [lb["name"] for lb in new_labels]
    for label_name in label_names:
        subprocess.run(
            ["gh", "issue", "edit", issue["number"],
             "--repo", issue["repo"], "--add-label", label_name],
            timeout=30,
        )
        print(f"  Added: {label_name}")

    # 留 comment 說明
    reasons = "\n".join([f"- `{lb['name']}`: {lb['reason']}" for lb in new_labels])
    comment = f"""### 🤖 績效標籤自動標記

{reasons}

> {summary}

_此標記由 AI 自動判斷。如有疑問請聯繫主管。_"""

    subprocess.run(
        ["gh", "issue", "comment", issue["number"],
         "--repo", issue["repo"], "--body", comment],
        timeout=30,
    )
    print(f"  Comment added to #{issue['number']}")


def main():
    print("=== Performance Auto Label ===")

    issue = get_issue_details()
    print(f"Issue: {issue['repo']}#{issue['number']} - {issue['title']}")

    labels = load_perf_labels()
    if not labels:
        print("No perf labels found, skipping")
        return

    # 取得 assignee 角色
    assignees = [a.strip() for a in issue["assignees"].split(",") if a.strip()]
    employee_roles = {}
    for a in assignees:
        role = load_employee_role(a)
        employee_roles[a] = role
    print(f"Assignees: {employee_roles}")

    # 如果已有 perf label 且不是 tier tag，跳過（避免重複標記）
    existing_perf = [
        lb for lb in issue["existing_labels"].split(",")
        if lb.startswith("perf:") and not lb.startswith("perf:tier-")
    ]
    if existing_perf:
        print(f"Already has perf labels: {existing_perf}, skipping AI analysis")
        return

    # 呼叫 AI
    prompt = build_prompt(issue, labels, employee_roles)
    print("Calling GitHub Copilot...")
    try:
        result = call_copilot(prompt)
        print(f"AI result: {json.dumps(result, ensure_ascii=False)}")
    except Exception as e:
        print(f"AI call failed: {e}", file=sys.stderr)
        return

    # 打上標籤
    apply_labels(issue, result)
    print("Done!")


if __name__ == "__main__":
    main()
