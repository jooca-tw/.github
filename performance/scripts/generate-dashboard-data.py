#!/usr/bin/env python3
"""
績效考核 Dashboard 資料產生器
從 GitHub org 的所有 repo 抓取 perf: label issues，
結合員工檔案，產出 data.json 供 Dashboard 前端使用。
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ORG = "jooca-tw"
REPO = ".github"
EMPLOYEES_DIR = Path("performance/employees")
OUTPUT_DIR = Path("performance/dashboard-out")
PERF_LABELS_PATH = Path("performance/perf-labels.json")

# 是否在 GitHub Actions 環境（有 checkout）
IN_CI = os.environ.get("CI") == "true" or EMPLOYEES_DIR.exists()


def run_gh(args: list[str]) -> str:
    """執行 gh CLI 並回傳 stdout。"""
    result = subprocess.run(
        ["gh", "api", *args],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        print(f"gh api error: {result.stderr}", file=sys.stderr)
        return "[]"
    return result.stdout


def load_employees() -> dict:
    """讀取所有員工 YAML 檔案（CI 讀本地，本地從 GitHub API 抓）。"""
    employees = {}

    if IN_CI:
        files = list(EMPLOYEES_DIR.glob("*.yml"))
        for f in files:
            with open(f) as fh:
                data = yaml.safe_load(fh)
            if not data or not data.get("active", True):
                continue
            login = data.get("github_login", f.stem)
            employees[login] = _parse_employee(data, login)
    else:
        # 從 GitHub API 抓
        result = subprocess.run(
            ["gh", "api", f"repos/{ORG}/{REPO}/contents/performance/employees",
             "--jq", '.[].name'],
            capture_output=True, text=True, timeout=30,
        )
        for fname in result.stdout.strip().split("\n"):
            if not fname.endswith(".yml"):
                continue
            content_result = subprocess.run(
                ["gh", "api", f"repos/{ORG}/{REPO}/contents/performance/employees/{fname}",
                 "--jq", ".content"],
                capture_output=True, text=True, timeout=30,
            )
            import base64
            raw = base64.b64decode(content_result.stdout.strip()).decode()
            data = yaml.safe_load(raw)
            if not data or not data.get("active", True):
                continue
            login = data.get("github_login", fname.replace(".yml", ""))
            employees[login] = _parse_employee(data, login)

    return employees


def _parse_employee(data: dict, login: str) -> dict:
    return {
        "name": data.get("employee", login),
        "real_name": data.get("real_name", ""),
        "github_login": login,
        "role": data.get("role", ""),
        "joined": str(data.get("joined", "")),
        "manager": data.get("manager", ""),
        "projects": data.get("projects", []),
    }


def load_perf_labels() -> dict:
    """讀取 perf-labels.json（CI 讀本地，本地從 GitHub API 抓）。"""
    if IN_CI and PERF_LABELS_PATH.exists():
        with open(PERF_LABELS_PATH) as fh:
            labels = json.load(fh)
    else:
        import base64
        result = subprocess.run(
            ["gh", "api", f"repos/{ORG}/{REPO}/contents/performance/perf-labels.json",
             "--jq", ".content"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"Failed to fetch perf-labels.json: {result.stderr}", file=sys.stderr)
            return {}
        raw = base64.b64decode(result.stdout.strip()).decode()
        labels = json.loads(raw)

    return {lb["name"]: lb for lb in labels}


def fetch_perf_issues() -> list[dict]:
    """從 org 下所有 repo 搜尋帶 perf: label 的 issues。"""
    # 用 GitHub search API 一次撈整個 org
    query = f"org:{ORG} label:perf:hidden-bug,perf:milestone-missed,perf:surprise-delay,perf:untested-delivery,perf:customer-late-reply,perf:scope-creep,perf:tech-research,perf:ai-app,perf:crisis-handling,perf:team-backup,perf:tier-jump"

    # search API 用 gh search
    result = subprocess.run(
        [
            "gh", "search", "issues",
            "--owner", ORG,
            "--label", "perf:hidden-bug,perf:milestone-missed,perf:surprise-delay,perf:untested-delivery,perf:customer-late-reply,perf:scope-creep,perf:tech-research,perf:ai-app,perf:crisis-handling,perf:team-backup,perf:tier-jump",
            "--limit", "500",
            "--json", "number,title,state,labels,assignees,repository,closedAt,createdAt,url",
        ],
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode != 0:
        # search --label 用逗號是 OR，但 gh search issues 可能不支援多 label 一次搜
        # fallback: 逐 label 搜尋
        print(f"Batch search failed, falling back to per-label search: {result.stderr}", file=sys.stderr)
        return fetch_perf_issues_per_label()

    return json.loads(result.stdout) if result.stdout.strip() else []


def fetch_perf_issues_per_label() -> list[dict]:
    """逐個 perf label 搜尋 issues（fallback）。"""
    perf_label_names = [
        "perf:hidden-bug", "perf:milestone-missed", "perf:surprise-delay",
        "perf:untested-delivery", "perf:customer-late-reply", "perf:scope-creep",
        "perf:tech-research", "perf:ai-app", "perf:crisis-handling",
        "perf:team-backup", "perf:tier-jump",
    ]
    seen = set()
    all_issues = []
    for label in perf_label_names:
        result = subprocess.run(
            [
                "gh", "search", "issues",
                "--owner", ORG,
                "--label", label,
                "--limit", "200",
                "--json", "number,title,state,labels,assignees,repository,closedAt,createdAt,url",
            ],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            print(f"Search failed for {label}: {result.stderr}", file=sys.stderr)
            continue
        issues = json.loads(result.stdout) if result.stdout.strip() else []
        for issue in issues:
            key = issue.get("url", "")
            if key not in seen:
                seen.add(key)
                all_issues.append(issue)
    return all_issues


def build_dashboard_data(employees: dict, perf_labels: dict, issues: list[dict]) -> dict:
    """組合成 Dashboard 所需的 data.json 結構。"""
    now = datetime.now(timezone.utc).isoformat()

    # 初始化每位員工的績效資料
    employee_scores = {}
    for login, emp in employees.items():
        employee_scores[login] = {
            **emp,
            "total_score": 0,
            "deductions": 0,
            "bonuses": 0,
            "issues": [],
            "dimensions": {"O1": 0, "O2": 0, "O3": 0, "O4": 0, "O5": 0},
            "labels_count": {},
        }

    # 處理每個 issue
    for issue in issues:
        assignees = [a.get("login", "") for a in issue.get("assignees", [])]
        issue_labels = [lb.get("name", "") for lb in issue.get("labels", [])]
        perf_issue_labels = [lb for lb in issue_labels if lb.startswith("perf:")]
        repo_name = issue.get("repository", {}).get("name", "") if isinstance(issue.get("repository"), dict) else str(issue.get("repository", ""))

        # 找出這個 issue 的 tier
        tier = None
        for lb in issue_labels:
            if lb.startswith("perf:tier-"):
                tier = lb

        issue_record = {
            "number": issue.get("number"),
            "title": issue.get("title", ""),
            "state": issue.get("state", ""),
            "repo": repo_name,
            "url": issue.get("url", ""),
            "created_at": issue.get("createdAt", ""),
            "closed_at": issue.get("closedAt", ""),
            "perf_labels": perf_issue_labels,
            "tier": tier,
        }

        for assignee in assignees:
            if assignee not in employee_scores:
                continue

            emp = employee_scores[assignee]
            emp["issues"].append(issue_record)

            for lb_name in perf_issue_labels:
                if lb_name.startswith("perf:tier-"):
                    continue
                label_def = perf_labels.get(lb_name, {})
                label_type = label_def.get("type", "")
                score = label_def.get("score", 0)
                dimension = label_def.get("dimension", "")

                # 加分項用 score_range 的中位值（實際分數應從 issue comment 的 /confirm 抓取）
                if "score_range" in label_def:
                    sr = label_def["score_range"]
                    score = (sr[0] + sr[1]) // 2

                emp["total_score"] += score
                if label_type == "deduction":
                    emp["deductions"] += score
                elif label_type == "bonus":
                    emp["bonuses"] += score

                if dimension in emp["dimensions"]:
                    emp["dimensions"][dimension] += score

                emp["labels_count"][lb_name] = emp["labels_count"].get(lb_name, 0) + 1

    # 計算 alerts
    alerts = []
    for login, emp in employee_scores.items():
        if emp.get("role") == "senior-rd-b" and emp.get("manager") == "":
            continue  # 部門主管不列入警示

        # 連續扣分警示
        deduction_count = sum(1 for lb, cnt in emp["labels_count"].items()
                             if perf_labels.get(lb, {}).get("type") == "deduction"
                             for _ in range(cnt))
        if deduction_count >= 3:
            alerts.append({
                "login": login,
                "name": emp["real_name"] or emp["name"],
                "severity": "red",
                "message": f"累計 {deduction_count} 次扣分事件",
            })
        elif deduction_count >= 2:
            alerts.append({
                "login": login,
                "name": emp["real_name"] or emp["name"],
                "severity": "yellow",
                "message": f"累計 {deduction_count} 次扣分事件",
            })

        # 從未加分警示
        if emp["bonuses"] == 0 and len(emp["issues"]) > 0:
            alerts.append({
                "login": login,
                "name": emp["real_name"] or emp["name"],
                "severity": "yellow",
                "message": "有績效事件但從未獲得加分",
            })

    # 部門統計
    active_employees = [e for e in employee_scores.values() if e.get("manager")]
    dept_stats = {
        "total_employees": len(active_employees),
        "avg_score": round(sum(e["total_score"] for e in active_employees) / max(len(active_employees), 1), 1),
        "total_issues": sum(len(e["issues"]) for e in active_employees),
        "total_deductions": sum(e["deductions"] for e in active_employees),
        "total_bonuses": sum(e["bonuses"] for e in active_employees),
    }

    return {
        "generated_at": now,
        "org": ORG,
        "department_stats": dept_stats,
        "employees": employee_scores,
        "alerts": alerts,
        "perf_labels": {k: {
            "name": v["name"],
            "color": v.get("color", ""),
            "description": v.get("description", ""),
            "type": v.get("type", ""),
            "score": v.get("score", 0),
            "score_range": v.get("score_range"),
            "dimension": v.get("dimension", ""),
        } for k, v in perf_labels.items()},
    }


def main():
    print("Loading employees...")
    employees = load_employees()
    print(f"  Found {len(employees)} active employees")

    print("Loading perf labels...")
    perf_labels = load_perf_labels()
    print(f"  Found {len(perf_labels)} labels")

    print("Fetching perf issues from GitHub...")
    issues = fetch_perf_issues()
    print(f"  Found {len(issues)} issues with perf labels")

    print("Building dashboard data...")
    data = build_dashboard_data(employees, perf_labels, issues)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "data.json"
    with open(output_path, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
