#!/usr/bin/env bash
# ==============================================================================
# RCAI (Root Cause AI) — Zero-Friction Drop-In Installer
# ==============================================================================
# Auto-discovers services in any Docker Compose project and boots RCAI
# with zero manual topology configuration.
#
# Usage:
#   ./install.sh                  # Interactive install in current directory
#   ./install.sh -f compose.yml   # Specify custom compose file
#   ./install.sh -y               # Non-interactive / auto-confirm (CI mode)
#   ./install.sh --dry-run        # Inspect topology without starting containers
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE=""
AUTO_CONFIRM=false
DRY_RUN=false
SCRAPE_DIR="${SCRIPT_DIR}/.rcai"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)
      COMPOSE_FILE="$2"
      shift 2
      ;;
    -y|--yes)
      AUTO_CONFIRM=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [-f <compose-file>] [-y|--yes] [--dry-run]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo "===================================================================="
echo "    RCAI (Root Cause AI) — Drop-In Auto-Discovery Installer        "
echo "===================================================================="

# Locate compose manifest if not specified
if [[ -z "$COMPOSE_FILE" ]]; then
  for candidate in "docker-compose.yml" "compose.yml" "docker-compose.yaml" "compose.yaml"; do
    if [[ -f "$candidate" ]]; then
      COMPOSE_FILE="$candidate"
      break
    fi
  done
fi

if [[ -z "$COMPOSE_FILE" || ! -f "$COMPOSE_FILE" ]]; then
  echo "Error: No docker-compose manifest found in current directory." >&2
  echo "Please specify one using: $0 -f /path/to/docker-compose.yml" >&2
  exit 1
fi

echo "Inspecting Compose manifest: ${COMPOSE_FILE} ..."
echo ""

# Run inspector script
PYTHON_BIN="python3"
if [[ -f "${SCRIPT_DIR}/.venv/bin/python3" ]]; then
  PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python3"
fi

INSPECTOR="${SCRIPT_DIR}/scripts/inspect_compose.py"
PROMETHEUS_OUT="${SCRAPE_DIR}/prometheus.yml"

# Output topology discovery summary and generate scrape config
"$PYTHON_BIN" "$INSPECTOR" -f "$COMPOSE_FILE" --write-scrape-config "$PROMETHEUS_OUT"

echo ""
echo "Prometheus scrape configuration generated: ${PROMETHEUS_OUT}"
echo "===================================================================="

if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY-RUN] Discovery completed. To launch RCAI:"
  echo "  docker compose -f ${COMPOSE_FILE} -f ${SCRIPT_DIR}/docker-compose.snippet.yml up -d"
  exit 0
fi

# Prompt confirmation unless -y was passed
if [[ "$AUTO_CONFIRM" != true ]]; then
  read -r -p "Start RCAI against this topology? [Y/n] " response
  response=${response,,} # lowercase
  if [[ "$response" =~ ^(no|n)$ ]]; then
    echo "Installation aborted by user."
    exit 0
  fi
fi

echo ""
echo "Booting RCAI with drop-in auto-discovery..."

# Check docker compose availability
COMPOSE_CMD=""
if docker compose version &>/dev/null; then
  COMPOSE_CMD="docker compose"
elif which docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
fi

if [[ -z "$COMPOSE_CMD" ]]; then
  echo "Warning: 'docker compose' command not found on host PATH."
  echo "You can run RCAI by installing docker compose and executing:"
  echo "  docker compose -f ${COMPOSE_FILE} -f ${SCRIPT_DIR}/docker-compose.snippet.yml up -d"
  exit 0
fi

# Check Docker daemon connectivity
if ! docker info &>/dev/null; then
  echo "Warning: Docker daemon is not running or current user lacks socket permissions."
  echo "To launch RCAI once Docker is active:"
  echo "  ${COMPOSE_CMD} -f ${COMPOSE_FILE} -f ${SCRIPT_DIR}/docker-compose.snippet.yml up -d"
  exit 0
fi

${COMPOSE_CMD} -f "$COMPOSE_FILE" -f "${SCRIPT_DIR}/docker-compose.snippet.yml" up -d

echo ""
echo "===================================================================="
echo " RCAI is running with Auto-Discovery Mode enabled!                  "
echo "                                                                    "
echo " Investigation Console API: http://localhost:8000                   "
echo " Health Status:             http://localhost:8000/health            "
echo " Live Discovered Topology:  http://localhost:8000/api/topology      "
echo " Prometheus Scraper:        http://localhost:9090                   "
echo "===================================================================="
