#!/usr/bin/env python3
"""
績效考核 Dashboard 資料產生器
從 GitHub org 的所有 repo 抓取 perf: label issues，
結合員工檔案，產出 data.json 供 Dashboard 前端使用。
輸出格式符合 data.schema.json（stats / members / alerts / alert_summary）。
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

IN_CI = os.environ.get("CI") == "true" or EMPLOYEES_DIR.exists()

# 考核維度對應
DIMENSIONS = {
    "O1": "程式碼品質",
    "O2": "時程管理",
    "O3": "團隊協作",
    "O4": "技術成長",
    "O5": "客戶滿意度",
}

CATEGORIES = ["程式碼品質", "時程管理", "團隊協作", "技術成長", "問題解決", "客戶滿意度"]
CATEGORY_COLORS = {
    "程式碼品質": "#f85149",
    "時程管理": "#2f81f7",
    "團隊協作": "#3fb950",
    "技術成長": "#a371f7",
    "問題解決": "#db6d28",
    "客戶滿意度": "#e3b341",
}

ROLE_LABELS = {
    "junior-rd": "初級工程師",
    "senior-rd-a": "資深工程師",
    "senior-rd-b": "資深工程師",
    "pm": "專案經理",
}

MONTHS_LABELS = ["11月", "12月", "1月", "2月", "3月", "4月"]


def load_employees() -> dict:
    employees = {}
    if IN_CI:
        for f in EMPLOYEES_DIR.glob("*.yml"):
            with open(f) as fh:
                data = yaml.safe_load(fh)
            if not data or not data.get("active", True):
                continue
            login = data.get("github_login", f.stem)
            employees[login] = data
    else:
        import base64
        result = subprocess.run(
            ["gh", "api", f"repos/{ORG}/{REPO}/contents/performance/employees",
             "--jq", ".[].name"],
            capture_output=True, text=True, timeout=30,
        )
        for fname in result.stdout.strip().split("\n"):
            if not fname.endswith(".yml"):
                continue
            cr = subprocess.run(
                ["gh", "api", f"repos/{ORG}/{REPO}/contents/performance/employees/{fname}",
                 "--jq", ".content"],
                capture_output=True, text=True, timeout=30,
            )
            raw = base64.b64decode(cr.stdout.strip()).decode()
            data = yaml.safe_load(raw)
            if not data or not data.get("active", True):
                continue
            login = data.get("github_login", fname.replace(".yml", ""))
            employees[login] = data
    return employees


def load_perf_labels() -> dict:
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
            ["gh", "search", "issues", "--owner", ORG, "--label", label,
             "--limit", "200",
             "--json", "number,title,state,labels,assignees,repository,closedAt,createdAt,url"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            continue
        issues = json.loads(result.stdout) if result.stdout.strip() else []
        for issue in issues:
            key = issue.get("url", "")
            if key not in seen:
                seen.add(key)
                all_issues.append(issue)
    return all_issues


def compute_score(label_def: dict) -> int:
    if "score" in label_def:
        return label_def["score"]
    if "score_range" in label_def:
        sr = label_def["score_range"]
        return (sr[0] + sr[1]) // 2
    return 0


def build_data(employees: dict, perf_labels: dict, issues: list[dict]) -> dict:
    now = datetime.now(timezone.utc)

    # Per-employee accumulators
    emp_data = {}
    for login, raw in employees.items():
        manager = raw.get("manager", "")
        # Skip department head (no manager)
        role_key = raw.get("role", "")
        real_name = raw.get("real_name", raw.get("employee", login))
        name = raw.get("employee", login)

        emp_data[login] = {
            "login": login,
            "name": real_name,
            "display_name": name,
            "role": ROLE_LABELS.get(role_key, role_key),
            "role_key": role_key,
            "manager": manager,
            "projects": raw.get("projects", []),
            "total_score": 60,  # baseline
            "deductions": 0,
            "bonuses": 0,
            "dim_scores": {d: 0 for d in DIMENSIONS},
            "issue_list": [],
            "labels_hit": {},
        }

    # Process issues
    for issue in issues:
        assignees = [a.get("login", "") for a in issue.get("assignees", [])]
        issue_labels = [lb.get("name", "") for lb in issue.get("labels", [])]
        perf_issue_labels = [lb for lb in issue_labels if lb.startswith("perf:") and not lb.startswith("perf:tier-")]
        repo = issue.get("repository", {})
        repo_name = repo.get("name", "") if isinstance(repo, dict) else str(repo)

        # Map labels to categories
        category = "問題解決"  # default
        for lb in perf_issue_labels:
            dim = perf_labels.get(lb, {}).get("dimension", "")
            if dim in DIMENSIONS:
                category = DIMENSIONS[dim]
                break

        status = "已完成" if issue.get("state") == "CLOSED" else "進行中"

        issue_rec = {
            "id": f"#{issue.get('number', '?')}",
            "title": issue.get("title", ""),
            "category": category,
            "status": status,
            "url": issue.get("url", ""),
        }

        for assignee in assignees:
            if assignee not in emp_data:
                continue
            emp = emp_data[assignee]
            emp["issue_list"].append(issue_rec)

            for lb_name in perf_issue_labels:
                label_def = perf_labels.get(lb_name, {})
                score = compute_score(label_def)
                label_type = label_def.get("type", "")
                dimension = label_def.get("dimension", "")

                emp["total_score"] += score
                if label_type == "deduction":
                    emp["deductions"] += score
                elif label_type == "bonus":
                    emp["bonuses"] += score
                if dimension in emp["dim_scores"]:
                    emp["dim_scores"][dimension] += score
                emp["labels_hit"][lb_name] = emp["labels_hit"].get(lb_name, 0) + 1

    # Build members array (design schema)
    members = []
    for login, emp in emp_data.items():
        if not emp["manager"]:
            continue  # skip dept head

        score = max(0, min(100, emp["total_score"]))
        tier = score_to_tier(score)
        alert = compute_alert(emp, perf_labels)

        # Build trend (placeholder: flat line at current score for now)
        trend_overall = [score] * 6

        trend_categories = [{"name": c, "color": CATEGORY_COLORS[c]} for c in CATEGORIES]
        trend_series = {c: [score] * 6 for c in CATEGORIES}

        # Focus tags: categories where deductions happened
        focus_tags = []
        for lb_name, cnt in emp["labels_hit"].items():
            ld = perf_labels.get(lb_name, {})
            if ld.get("type") == "deduction":
                dim = ld.get("dimension", "")
                cat = DIMENSIONS.get(dim, "")
                if cat and cat not in focus_tags:
                    focus_tags.append(cat)

        # KPIs
        kpis = []
        for cat in CATEGORIES:
            cat_score = score  # simplified: same as overall for now
            kpis.append({
                "name": cat,
                "score": cat_score,
                "prev": cat_score,
                "delta": 0,
                "status": "已完成" if cat_score >= 60 else "未達標",
                "trend": [cat_score] * 6,
            })

        initials_str = emp["name"][-2:] if len(emp["name"]) >= 2 else emp["name"]

        members.append({
            "name": emp["name"],
            "initials": initials_str,
            "role": emp["role"],
            "team": ", ".join(emp["projects"][:2]) if emp["projects"] else "",
            "subtitle": f"{emp['role']} · {emp['login']}",
            "tier": tier,
            "alert": alert,
            "issues": len(emp["issue_list"]),
            "current_score": score,
            "focus_tags": focus_tags,
            "trend": {
                "overall": trend_overall,
                "months": MONTHS_LABELS,
                "categories": trend_categories,
                "series": trend_series,
            },
            "kpis": kpis,
            "issue_list": emp["issue_list"],
        })

    # Build alerts
    alerts = []
    alert_counts = {"red": 0, "orange": 0, "amber": 0}
    for m in members:
        if m["alert"] == "ok":
            continue
        level = m["alert"]
        alert_counts[level] = alert_counts.get(level, 0) + 1

        reason = ""
        detail = ""
        if level == "red":
            reason = "累計多次扣分"
            detail = f"score {m['current_score']} · tier {m['tier']}"
        elif level == "orange":
            reason = "扣分事件"
            detail = f"score {m['current_score']}"
        elif level == "amber":
            reason = "需要觀察"
            detail = f"score {m['current_score']}"

        alerts.append({
            "name": m["name"],
            "initials": m["initials"],
            "tier": m["tier"],
            "level": level,
            "reason": reason,
            "detail": detail,
            "date": now.strftime("%-m/%-d"),
        })

    # Sort alerts: red > orange > amber, then by date
    level_order = {"red": 0, "orange": 1, "amber": 2}
    alerts.sort(key=lambda a: level_order.get(a["level"], 3))

    # Stats
    scores = [m["current_score"] for m in members]
    avg_score = round(sum(scores) / max(len(scores), 1), 1)
    sa_count = sum(1 for m in members if m["tier"] in ("S", "A"))
    total_issues = sum(m["issues"] for m in members)
    alerts_count = len(alerts)

    stats = {
        "department_name": "O 部門",
        "period_label": now.strftime("%Y 年 %-m 月"),
        "member_count": len(members),
        "avg_score": avg_score,
        "avg_score_delta": "—",
        "completion_rate": f"{round(avg_score)}%",
        "completion_rate_delta": "—",
        "total_issues": total_issues,
        "sa_tier_count": sa_count,
        "alerts_count": alerts_count,
        "alerts_delta": "—",
    }

    return {
        "stats": stats,
        "members": members,
        "alerts": alerts,
        "alert_summary": alert_counts,
    }


def score_to_tier(score: int) -> str:
    if score >= 90:
        return "S"
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def compute_alert(emp: dict, perf_labels: dict) -> str:
    deduction_count = sum(
        cnt for lb, cnt in emp["labels_hit"].items()
        if perf_labels.get(lb, {}).get("type") == "deduction"
    )
    # No perf events at all → ok (system just started)
    if not emp["labels_hit"] and not emp["issue_list"]:
        return "ok"

    score = max(0, min(100, emp["total_score"]))

    if deduction_count >= 3 or score < 50:
        return "red"
    if deduction_count >= 2 or score < 65:
        return "orange"
    if deduction_count >= 1 or score < 70:
        return "amber"
    return "ok"


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
    data = build_data(employees, perf_labels, issues)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "data.json"
    with open(output_path, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"Written to {output_path} ({len(data['members'])} members, {len(data['alerts'])} alerts)")


if __name__ == "__main__":
    main()
