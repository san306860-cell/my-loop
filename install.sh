#!/usr/bin/env bash
# 把仓库里的 my-loop skill 装到这台机器上所有 coding agent 的 skill 区。
# 幂等：每次全量覆盖，并清掉已退役的 skill。改完 skill 跑一遍就行。
#
#   ./install.sh            装
#   ./install.sh --dry-run  只看会动哪些目录
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"
DRY=${1:-}

# 各家 agent 的 skill 区。目录不存在就建（pi/dsh/devin 尚未建过）。
# ~/.agents/skills 是公用区：agy / pi / dsh / codex 都读它，~/.claude/skills 软链到它。
ROOTS=(
  "$HOME/.agents/skills"          # 公用区（agy, pi, dsh, codex 共读）
  "$HOME/.codex/skills"           # codex
  "$HOME/.pi/skills"              # pi
  "$HOME/.dsh/skills"             # dsh
  "$HOME/.devin/skills"           # devin
  "$HOME/.cursor/skills"          # cursor
  "$HOME/.mirasim/skills"         # mirasim
  "$HOME/.gemini/config/skills"   # gemini
)

CURRENT=(my-loop-pm my-loop-worker my-loop-review my-loop-eli5)
RETIRED=(my-loop-docs)            # v3.1 砍掉，装到哪清到哪

for root in "${ROOTS[@]}"; do
  echo "→ $root"
  [ -n "$DRY" ] && continue
  mkdir -p "$root"
  for s in "${RETIRED[@]}" "${CURRENT[@]}"; do rm -rf "${root:?}/$s"; done
  for s in "${CURRENT[@]}"; do cp -R "$SRC/$s" "$root/$s"; done
  find "$root" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
done

# ~/.claude/skills 用软链指向公用区（Claude Code 原本就是这个约定，保持不变）。
CL="$HOME/.claude/skills"
if [ -d "$CL" ] && [ -z "$DRY" ]; then
  echo "→ $CL (软链 → ~/.agents/skills)"
  for s in "${RETIRED[@]}"; do rm -rf "${CL:?}/$s"; done
  for s in "${CURRENT[@]}"; do rm -rf "${CL:?}/$s"; ln -s "$HOME/.agents/skills/$s" "$CL/$s"; done
fi

[ -n "$DRY" ] || echo "✓ 装了 ${#CURRENT[@]} 个 skill 到 ${#ROOTS[@]} 个 skill 区，清掉 ${RETIRED[*]}"
