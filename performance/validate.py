#!/usr/bin/env python3
"""Validate O 部門績效考核員工檔。

Usage:
    python validate.py                      # 驗證 performance/employees/ 下所有檔
    python validate.py <file1.yml> [file2]  # 驗證指定檔案

Exit 0 通過，exit 1 失敗。可在 GitHub Action 中呼叫。
"""
from __future__ import annotations
import sys
import re
import json
import pathlib
import urllib.request
import urllib.error

try:
    import yaml
except ImportError:
    print("::error::需要 pyyaml（pip install pyyaml）", file=sys.stderr)
    sys.exit(2)

try:
    from jsonschema import Draft7Validator, FormatChecker
except ImportError:
    print("::error::需要 jsonschema（pip install jsonschema）", file=sys.stderr)
    sys.exit(2)

SCHEMA: dict = {
    "type": "object",
    "required": ["employee", "github_login", "real_name", "email", "role", "joined", "active"],
    "additionalProperties": False,
    "properties": {
        "employee":     {"type": "string", "minLength": 1},
        "github_login": {"type": "string", "pattern": r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$"},
        "real_name":    {"type": "string", "minLength": 1},
        "email":        {"type": "string", "format": "email"},
        "role":         {"enum": ["junior-rd", "senior-rd-a", "senior-rd-b", "pm"]},
        "joined":       {"type": "string", "format": "date"},
        "manager":      {"type": ["string", "null"], "pattern": r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$"},
        "manager_name": {"type": ["string", "null"], "minLength": 1},
        "active":       {"type": "boolean"},
        "left_at":      {"type": "string", "format": "date"},
        "notes":        {"type": "string"},
        "projects":    {"type": "array", "items": {"type": "string"}},
    },
    "allOf": [
        {"if": {"properties": {"active": {"const": False}}}, "then": {"required": ["left_at"]}},
        {"anyOf": [{"required": ["manager"]}, {"required": ["manager_name"]}]},
    ],
}

EMPLOYEES_DIR = pathlib.Path(__file__).parent / "employees"
GITHUB_API = "https://api.github.com"


def github_user_exists(login: str, token: str | None) -> bool:
    req = urllib.request.Request(f"{GITHUB_API}/users/{login}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise
    except Exception:
        return False


def gh_annotate(level: str, file: str, msg: str) -> None:
    # GitHub Actions annotation syntax
    print(f"::{level} file={file}::{msg}")


def validate_file(path: pathlib.Path, all_logins: set[str], github_token: str | None) -> list[str]:
    errors: list[str] = []
    rel = str(path.relative_to(EMPLOYEES_DIR.parent.parent)) if EMPLOYEES_DIR.parent.parent in path.parents else str(path)

    # 1. YAML parse
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        errors.append(f"YAML 解析失敗: {e}")
        return errors

    if not isinstance(data, dict):
        errors.append("YAML 內容不是 object")
        return errors

    # 2. Schema
    validator = Draft7Validator(SCHEMA, format_checker=FormatChecker())
    for err in sorted(validator.iter_errors(data), key=lambda e: e.path):
        path_str = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"schema: {path_str}: {err.message}")

    if errors:
        return errors  # schema 沒過就不用做後續檢查

    # 3. 檔名 == github_login + .yml
    expected = f"{data['github_login']}.yml"
    if path.name != expected:
        errors.append(f"檔名不符：期望 {expected}，實際 {path.name}")

    # 4. manager 與 manager_name 擇一警告
    if data.get("manager") and data.get("manager_name"):
        gh_annotate("warning", rel, "manager 與 manager_name 同時有值，manager 優先，manager_name 忽略")

    # 5. manager 必須是另一份檔的 github_login
    mgr = data.get("manager")
    if mgr and mgr not in all_logins:
        errors.append(f"manager '{mgr}' 在 employees/ 下找不到對應檔案")

    # 6. github_login 必須真實存在於 GitHub（optional，沒 token 時跳過）
    if github_token:
        if not github_user_exists(data["github_login"], github_token):
            errors.append(f"github_login '{data['github_login']}' 在 GitHub 上不存在")

    return errors


def main() -> int:
    import os
    github_token = os.environ.get("GITHUB_TOKEN")

    if not EMPLOYEES_DIR.exists():
        print(f"::error::employees 目錄不存在: {EMPLOYEES_DIR}", file=sys.stderr)
        return 1

    # 收集所有存在的 github_login（用於 manager 交叉檢查）
    all_logins: set[str] = set()
    for p in EMPLOYEES_DIR.glob("*.yml"):
        try:
            d = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(d, dict) and "github_login" in d:
                all_logins.add(d["github_login"])
        except Exception:
            pass

    # 決定要驗哪些檔
    if len(sys.argv) > 1:
        targets = [pathlib.Path(p) for p in sys.argv[1:]]
    else:
        targets = sorted(EMPLOYEES_DIR.glob("*.yml"))

    total = 0
    failed = 0
    for path in targets:
        if not path.exists():
            print(f"❌ {path}: 檔案不存在")
            failed += 1
            total += 1
            continue
        total += 1
        errs = validate_file(path, all_logins, github_token)
        if errs:
            failed += 1
            for e in errs:
                gh_annotate("error", str(path.name), e)
            print(f"❌ {path.name}")
            for e in errs:
                print(f"   - {e}")
        else:
            print(f"✅ {path.name}")

    print()
    print(f"驗證結果：{total - failed} 通過 / {failed} 失敗 / {total} 總計")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
