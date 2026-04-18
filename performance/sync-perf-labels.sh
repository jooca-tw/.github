#!/bin/bash
# 把 perf:* label 同步到 O 部門所有 repo（簡化版 12 核心 + 5 tier tag）
# Usage:
#   bash sync-perf-labels.sh                # 同步到所有 jooca-tw repo
#   bash sync-perf-labels.sh <repo-name>    # 只同步到單一 repo（試跑用）
#   DRY_RUN=1 bash sync-perf-labels.sh      # 預覽不寫入
set -e

ORG="${ORG:-jooca-tw}"
LABELS_FILE="$(dirname "$0")/perf-labels.json"

if [ ! -f "$LABELS_FILE" ]; then
  echo "❌ Labels file not found: $LABELS_FILE"
  exit 1
fi

# 決定目標 repo 清單
if [ -n "$1" ]; then
  REPOS="$1"
  echo "🎯 Target: single repo $ORG/$1"
else
  echo "🎯 Target: all repos in $ORG"
  REPOS=$(gh repo list "$ORG" --limit 100 --json name --jq '.[].name')
fi

TOTAL_REPOS=$(echo "$REPOS" | wc -l | tr -d ' ')
TOTAL_LABELS=$(jq 'length' "$LABELS_FILE")

echo "📦 $TOTAL_LABELS labels × $TOTAL_REPOS repos"
[ -n "$DRY_RUN" ] && echo "🔍 DRY_RUN mode (no changes will be made)"
echo

for repo in $REPOS; do
  echo "=== $ORG/$repo ==="

  jq -c '.[]' "$LABELS_FILE" | while read -r label; do
    name=$(echo "$label" | jq -r '.name')
    color=$(echo "$label" | jq -r '.color')
    desc=$(echo "$label" | jq -r '.description')

    if [ -n "$DRY_RUN" ]; then
      echo "  [dry] $name ($color)"
      continue
    fi

    if gh label create "$name" \
      --repo "$ORG/$repo" \
      --color "$color" \
      --description "$desc" \
      --force > /dev/null 2>&1; then
      echo "  ✅ $name"
    else
      echo "  ⚠️  failed: $name"
    fi
  done
  echo
done

echo "🎉 Sync completed."
