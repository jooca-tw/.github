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

# v5.1 三軸架構（取代 v3 的 O1-O5 五維度）
AXES = {
    "axis1-ai-adoption": "AI 導入",
    "axis2-on-time": "如期交付",
    "axis3-quality": "品質",
    "general": "通用",
}

# v3 兼容：dimension → axis 對應（avoid breaking existing data）
DIMENSION_TO_AXIS = {
    "O1": "axis3-quality",      # 程式碼品質 → 品質
    "O2": "axis2-on-time",      # 時程管理 → 如期
    "O3": "axis2-on-time",      # 團隊協作 → 如期（review-lag 也歸這軸）
    "O4": "general",            # 技術成長 → 通用
    "O5": "axis1-ai-adoption",  # 客戶滿意度 → 改 AI 導入（v3 ai-app 在 O5）
}

CATEGORIES = ["AI 導入", "如期交付", "品質", "通用"]
CATEGORY_COLORS = {
    "AI 導入": "#a371f7",
    "如期交付": "#2f81f7",
    "品質": "#f85149",
    "通用": "#8b949e",
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
        # v5.1 軸2 如期
        "perf:milestone-missed", "perf:surprise-delay",
        "perf:customer-late-reply",
        "perf:review-lag",
        # v5.2 scope-creep 三級拆分
        "perf:scope-creep-external-handled",
        "perf:scope-creep-external-unmanaged",
        "perf:scope-creep-internal",
        "perf:change-management-good",
        # v5.3 需求變更
        "perf:requirement-change", "perf:rework-credit",
        "perf:spec-not-frozen",
        # v5.1 軸3 品質
        "perf:hidden-bug", "perf:quality-rollback", "perf:customer-bug",
        # v5.1 軸1 AI 導入
        "perf:ai-contribution", "perf:ai-zero",
        # 通用加分（保留）
        "perf:tech-research", "perf:crisis-handling",
        "perf:team-backup", "perf:tier-jump",
        # v3/v5.1 相容（暫保留以支援過渡期歷史資料）
        "perf:scope-creep", "perf:untested-delivery",
        "perf:ai-app", "perf:ai-paired",
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


def compute_score(label_def: dict, role: str = "rd") -> int:
    """計算 label 對指定 role 的得分。
    支援 v5.1 milestone-missed 拆分（score_pm / score_rd）。"""
    # milestone-missed 等拆分型 label
    if role == "pm" and "score_pm" in label_def:
        return label_def["score_pm"]
    if role == "rd" and "score_rd" in label_def:
        return label_def["score_rd"]
    if "score" in label_def:
        return label_def["score"]
    if "score_range" in label_def:
        sr = label_def["score_range"]
        return (sr[0] + sr[1]) // 2
    return 0


def get_label_axis(label_def: dict) -> str:
    """取得 label 的 axis（v5.1）。回退到舊 dimension 對應"""
    axis = label_def.get("axis")
    if axis:
        return axis
    dim = label_def.get("dimension", "")
    return DIMENSION_TO_AXIS.get(dim, "general")


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
            "system_type": raw.get("system_type", "general"),  # v5.1: legacy / new-feature / internal-tooling / general
            "total_score": 60,  # baseline
            "deductions": 0,
            "bonuses": 0,
            "axis_scores": {a: 0 for a in AXES},  # v5.1 三軸
            "issue_list": [],
            "labels_hit": {},
            "review_lag_count": 0,  # 月度 review-lag 件數（用於上限 -5 計算）
        }

    # Process issues
    for issue in issues:
        assignees = [a.get("login", "") for a in issue.get("assignees", [])]
        issue_labels = [lb.get("name", "") for lb in issue.get("labels", [])]
        perf_issue_labels = [lb for lb in issue_labels if lb.startswith("perf:") and not lb.startswith("perf:tier-")]
        repo = issue.get("repository", {})
        repo_name = repo.get("name", "") if isinstance(repo, dict) else str(repo)

        # Map labels to categories（v5.1 三軸）
        category = "通用"  # default
        for lb in perf_issue_labels:
            ax = get_label_axis(perf_labels.get(lb, {}))
            if ax in AXES:
                category = AXES[ax]
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
                role_key = emp.get("role_key", "rd")
                # 抽出 role：pm 角色獨立處理 milestone-missed
                role_for_score = "pm" if "pm" in role_key else "rd"
                score = compute_score(label_def, role=role_for_score)
                label_type = label_def.get("type", "")
                axis = get_label_axis(label_def)

                # review-lag 月度上限 -5
                if lb_name == "perf:review-lag":
                    emp["review_lag_count"] += 1
                    if emp["review_lag_count"] > 5:
                        # 已達月度上限 -5，後續不再扣
                        score = 0

                # v5.3 rework-credit 月度上限 +5
                if lb_name == "perf:rework-credit":
                    emp.setdefault("rework_credit_count", 0)
                    emp["rework_credit_count"] += 1
                    if emp["rework_credit_count"] > 5:
                        score = 0

                emp["total_score"] += score
                if label_type == "deduction":
                    emp["deductions"] += score
                elif label_type == "bonus":
                    emp["bonuses"] += score
                if axis in emp["axis_scores"]:
                    emp["axis_scores"][axis] += score
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

        # Focus tags: categories where deductions happened (v5.1 三軸)
        focus_tags = []
        for lb_name, cnt in emp["labels_hit"].items():
            ld = perf_labels.get(lb_name, {})
            if ld.get("type") == "deduction":
                ax = get_label_axis(ld)
                cat = AXES.get(ax, "")
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

    # v5.1 團隊 KPI（三軸 leading indicator，全員可見）
    team_kpi = build_team_kpi(emp_data, issues, perf_labels)

    return {
        "stats": stats,
        "team_kpi": team_kpi,
        "members": members,
        "alerts": alerts,
        "alert_summary": alert_counts,
    }


def build_team_kpi(emp_data: dict, issues: list[dict], perf_labels: dict) -> dict:
    """v5.1 團隊層 leading indicator（dashboard 全員可見，按系統類型分組）"""
    # 篩選非主管
    members_only = {k: v for k, v in emp_data.items() if v.get("manager")}

    # 1. AI 導入率（個人保底達標 — 月內有 perf:ai-contribution 或無 perf:ai-zero）
    total = len(members_only) or 1
    ai_zero_count = sum(1 for v in members_only.values() if "perf:ai-zero" in v["labels_hit"])
    ai_active_count = total - ai_zero_count
    ai_adoption_rate = round(ai_active_count / total * 100)

    # 2. AI 流程貢獻者數
    ai_contrib_count = sum(1 for v in members_only.values() if "perf:ai-contribution" in v["labels_hit"])

    # 3. milestone 命中率（粗估：closed milestone 中無 perf:milestone-missed 比例）
    miss_count = sum(1 for i in issues
                     if any(lb.get("name") == "perf:milestone-missed" for lb in i.get("labels", [])))
    closed_milestone_count = sum(1 for v in members_only.values()
                                  for i in v.get("issue_list", [])
                                  if i.get("status") == "已完成")
    on_time_rate = round((1 - miss_count / max(closed_milestone_count, 1)) * 100) if closed_milestone_count else None

    # 4. 品質紅燈件數
    rollback_count = sum(v["labels_hit"].get("perf:quality-rollback", 0) for v in members_only.values())
    customer_bug_count = sum(v["labels_hit"].get("perf:customer-bug", 0) for v in members_only.values())
    hidden_bug_count = sum(v["labels_hit"].get("perf:hidden-bug", 0) for v in members_only.values())

    # 系統類型分組（避免劣幣驅良幣）
    by_system = {}
    for v in members_only.values():
        st = v.get("system_type", "general")
        by_system.setdefault(st, {"count": 0, "ai_zero": 0, "rollback": 0, "customer_bug": 0})
        by_system[st]["count"] += 1
        if "perf:ai-zero" in v["labels_hit"]:
            by_system[st]["ai_zero"] += 1
        by_system[st]["rollback"] += v["labels_hit"].get("perf:quality-rollback", 0)
        by_system[st]["customer_bug"] += v["labels_hit"].get("perf:customer-bug", 0)

    # v5.2 客戶插單頻率 + 變更管理覆蓋率
    scope_external_handled = sum(v["labels_hit"].get("perf:scope-creep-external-handled", 0) for v in members_only.values())
    scope_external_unmanaged = sum(v["labels_hit"].get("perf:scope-creep-external-unmanaged", 0) for v in members_only.values())
    scope_internal = sum(v["labels_hit"].get("perf:scope-creep-internal", 0) for v in members_only.values())
    scope_external_total = scope_external_handled + scope_external_unmanaged
    change_mgmt_coverage = round(scope_external_handled / scope_external_total * 100) if scope_external_total else None

    return {
        "axis1_ai_adoption": {
            "title": "軸 1：AI 導入",
            "ai_adoption_rate": ai_adoption_rate,  # %
            "ai_adoption_target": 70,
            "ai_zero_count": ai_zero_count,
            "ai_contributor_count": ai_contrib_count,
        },
        "axis2_on_time": {
            "title": "軸 2：如期交付",
            "milestone_hit_rate": on_time_rate,  # %（None = 無資料）
            "milestone_miss_count": miss_count,
            # v5.2 客戶插單變更管理
            "scope_external_total": scope_external_total,
            "scope_internal": scope_internal,
            "change_mgmt_coverage": change_mgmt_coverage,  # %（目標 ≥ 90）
            "change_mgmt_target": 90,
        },
        "axis3_quality": {
            "title": "軸 3：品質",
            "rollback_count": rollback_count,
            "customer_bug_count": customer_bug_count,
            "hidden_bug_count": hidden_bug_count,
        },
        "by_system_type": by_system,
        "note": "v5.1 leading indicator。個人考核只做紅燈，這份趨勢給全員看（鼓勵團隊層改善，避免個別比較）",
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
