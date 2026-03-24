#!/usr/bin/env bash
# .ai/sync.sh — Builds and syncs AI assistant instructions across platforms
# Usage: bash .ai/sync.sh [--global]
#
# Local (default): syncs project-level .ai/ → CLAUDE.md, AGENTS.md
# Global (--global): syncs ~/.ai/ → ~/CLAUDE.md, ~/AGENTS.md
#
# Platforms:
#   - Claude:        reads CLAUDE.md,  skills in .claude/commands/
#   - Gemini/Codex:  read  AGENTS.md,  skills in .agents/commands/
#
# Workflow:
#   1. Edit .ai/shared/instructions.md (shared context)
#   2. Edit .ai/claude/instructions.md or .ai/agents/instructions.md
#   3. Run: just ai-sync
#   4. Built files: CLAUDE.md, AGENTS.md
#   5. Shared skills copied to .claude/commands/ and .agents/commands/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Configuration -----------------------------------------------------------

# Platform definitions: "output_file:source_dir"
declare -A PLATFORMS=(
  [claude]="CLAUDE.md:claude"
  [agents]="AGENTS.md:agents"
)

# Where each platform looks for commands/skills
declare -A COMMAND_DIRS=(
  [claude]=".claude/commands"
  [agents]=".agents/commands"
)

# --- Functions ----------------------------------------------------------------

build_instructions() {
  local ai_dir="$1"
  local root_dir="$2"

  for platform in "${!PLATFORMS[@]}"; do
    IFS=':' read -r output_file platform_dir <<< "${PLATFORMS[$platform]}"

    local shared="$ai_dir/shared/instructions.md"
    local specific="$ai_dir/$platform_dir/instructions.md"
    local out="$root_dir/$output_file"

    # Start with shared instructions
    if [[ -f "$shared" ]]; then
      cat "$shared" > "$out"
    else
      echo "# Project Instructions" > "$out"
    fi

    # Append platform-specific instructions
    if [[ -f "$specific" ]]; then
      echo "" >> "$out"
      cat "$specific" >> "$out"
    fi

    echo "  Built: $output_file (shared + $platform_dir)"
  done
}

sync_skills() {
  local ai_dir="$1"
  local root_dir="$2"
  local skills_dir="$ai_dir/skills"

  if [[ ! -d "$skills_dir" ]] || [[ -z "$(ls -A "$skills_dir" 2>/dev/null)" ]]; then
    echo "  No shared skills to sync"
    return
  fi

  for platform in "${!COMMAND_DIRS[@]}"; do
    local cmd_dir="$root_dir/${COMMAND_DIRS[$platform]}"
    mkdir -p "$cmd_dir"

    local count=0
    for skill in "$skills_dir"/*.md; do
      [[ -f "$skill" ]] || continue

      local skill_name
      skill_name="$(basename "$skill")"
      local target="$cmd_dir/$skill_name"

      if [[ ! -f "$target" ]] || [[ "$skill" -nt "$target" ]]; then
        cp "$skill" "$target"
        ((count++))
      fi
    done

    echo "  ${COMMAND_DIRS[$platform]}/: $count skill(s) updated"
  done
}

# --- Main ---------------------------------------------------------------------

if [[ "${1:-}" == "--global" ]]; then
  AI_DIR="$HOME/.ai"
  ROOT_DIR="$HOME"
  echo "Syncing global (~/.ai/)..."
else
  AI_DIR="$SCRIPT_DIR"
  ROOT_DIR="$(dirname "$AI_DIR")"
  echo "Syncing local ($AI_DIR/)..."
fi

if [[ ! -d "$AI_DIR" ]]; then
  echo "Error: $AI_DIR does not exist. Create it first:"
  echo "  mkdir -p $AI_DIR/{shared,claude,agents,skills}"
  exit 1
fi

echo ""
echo "Building instruction files..."
build_instructions "$AI_DIR" "$ROOT_DIR"

echo ""
echo "Syncing shared skills..."
sync_skills "$AI_DIR" "$ROOT_DIR"

echo ""
echo "Done!"
