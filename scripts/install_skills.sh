#!/usr/bin/env bash
# Symlink one or more skills from ams-skills into an agent skills directory.
#
# Usage:
#   ./scripts/install_skills.sh                     # install all skills into .claude/skills
#   ./scripts/install_skills.sh --target ~/.codex/skills sar-adc dac bandgap
#   ./scripts/install_skills.sh --list
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${REPO_ROOT}/skills"
TARGET_DIR=".claude/skills"
LIST_ONLY=0
SELECTED=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target|-t)
            TARGET_DIR="$2"
            shift 2
            ;;
        --list|-l)
            LIST_ONLY=1
            shift
            ;;
        -h|--help)
            sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            SELECTED+=("$1")
            shift
            ;;
    esac
done

AVAILABLE=()
for d in "${SKILLS_DIR}"/*/; do
    [[ -f "${d}SKILL.md" ]] && AVAILABLE+=("$(basename "$d")")
done

if [[ "${LIST_ONLY}" -eq 1 ]]; then
    printf '%s\n' "${AVAILABLE[@]}"
    exit 0
fi

if [[ ${#SELECTED[@]} -eq 0 ]]; then
    SELECTED=("${AVAILABLE[@]}")
fi

mkdir -p "${TARGET_DIR}"

for s in "${SELECTED[@]}"; do
    src="${SKILLS_DIR}/${s}"
    if [[ ! -f "${src}/SKILL.md" ]]; then
        echo "ERROR: unknown skill '${s}'. Available: ${AVAILABLE[*]}" >&2
        exit 1
    fi
    dst="${TARGET_DIR}/${s}"
    ln -sfn "${src}" "${dst}"
    echo "Linked ${dst} -> ${src}"
done
