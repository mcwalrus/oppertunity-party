#!/usr/bin/env bash
# setup.sh — Bootstrap a development environment for the Opportunity Party project.
#
# Safe to run on a fresh machine or re-run on an existing one (idempotent).
# Requires macOS. Tested on Apple Silicon and Intel.
#
# Usage:
#   ./scripts/setup.sh
#
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${BLUE}▸${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
die()  { echo -e "${RED}✗${NC}  $*" >&2; exit 1; }
step() { echo -e "\n${BOLD}── $* ──${NC}"; }

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Guards ────────────────────────────────────────────────────────────────────
[[ "$OSTYPE" == "darwin"* ]] || die "This script is macOS-only."

echo -e "\n${BOLD}Opportunity Party — Dev Environment Setup${NC}"
echo "Project root: $PROJECT_ROOT"

# ─────────────────────────────────────────────────────────────────────────────
step "1 / 7  Homebrew"
# ─────────────────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    log "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Homebrew on Apple Silicon lands in /opt/homebrew; add to PATH for this session
    if [[ -x /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    ok "Homebrew installed"
else
    ok "Homebrew $(brew --version | head -1)"
fi

# ─────────────────────────────────────────────────────────────────────────────
step "2 / 7  Brew bundle"
# ─────────────────────────────────────────────────────────────────────────────
log "Installing Brewfile dependencies (this may take a minute on a fresh machine)..."
brew bundle --no-lock --file="$SCRIPT_DIR/Brewfile"
ok "All Brew dependencies satisfied"

# ─────────────────────────────────────────────────────────────────────────────
step "3 / 7  pi (AI coding agent)"
# ─────────────────────────────────────────────────────────────────────────────
if command -v pi &>/dev/null; then
    ok "pi already installed ($(pi --version 2>/dev/null || echo 'version unknown'))"
else
    log "Installing pi..."
    curl -fsSL https://pi.dev/install.sh | sh
    ok "pi installed"
fi

# ─────────────────────────────────────────────────────────────────────────────
step "4 / 7  Shell configuration"
# ─────────────────────────────────────────────────────────────────────────────
# Detect the user's login shell config file
case "$SHELL" in
    */zsh)  SHELL_RC="$HOME/.zshrc";  SHELL_NAME="zsh"  ;;
    */bash) SHELL_RC="$HOME/.bashrc"; SHELL_NAME="bash" ;;
    *)
        warn "Unrecognised shell ($SHELL) — skipping automatic shell config."
        warn "Add the fnm and direnv hooks to your shell's RC file manually."
        SHELL_RC=""; SHELL_NAME="" ;;
esac

if [[ -n "$SHELL_RC" ]]; then
    # fnm — Node version manager
    if grep -q 'fnm env' "$SHELL_RC" 2>/dev/null; then
        ok "fnm hook already in $SHELL_RC"
    else
        log "Adding fnm hook to $SHELL_RC..."
        {
            echo ''
            echo '# fnm — Node.js version manager (added by scripts/setup.sh)'
            # shellcheck disable=SC2016  # single quotes are intentional — written as literal to shell RC
            echo 'eval "$(fnm env --use-on-cd)"'
        } >> "$SHELL_RC"
        ok "fnm hook added to $SHELL_RC"
    fi

    # direnv
    if grep -q 'direnv hook' "$SHELL_RC" 2>/dev/null; then
        ok "direnv hook already in $SHELL_RC"
    else
        log "Adding direnv hook to $SHELL_RC..."
        {
            echo ''
            echo '# direnv — per-directory env vars (added by scripts/setup.sh)'
            echo "eval \"\$(direnv hook $SHELL_NAME)\""
        } >> "$SHELL_RC"
        ok "direnv hook added to $SHELL_RC"
    fi
fi

# Activate for this session so the rest of the script can use fnm/direnv
eval "$(fnm env --use-on-cd 2>/dev/null)" || true

# ─────────────────────────────────────────────────────────────────────────────
step "5 / 7  Node.js"
# ─────────────────────────────────────────────────────────────────────────────
NODE_VERSION_FILE="$PROJECT_ROOT/.node-version"
if [[ -f "$NODE_VERSION_FILE" ]]; then
    NODE_VERSION="$(cat "$NODE_VERSION_FILE")"
    log "Installing Node $NODE_VERSION (from .node-version)..."
    fnm install "$NODE_VERSION"
    fnm use "$NODE_VERSION"
else
    log "No .node-version found — installing latest Node LTS..."
    fnm install --lts
    fnm use lts-latest
fi
ok "Node $(node --version) active"

# ─────────────────────────────────────────────────────────────────────────────
step "6 / 7  Python dependencies"
# ─────────────────────────────────────────────────────────────────────────────
cd "$PROJECT_ROOT"
log "Syncing Python deps with uv (Python $(cat .python-version))..."
uv sync
ok "Python environment ready (.venv)"

# ─────────────────────────────────────────────────────────────────────────────
step "7 / 7  Site dependencies, git hooks & direnv"
# ─────────────────────────────────────────────────────────────────────────────
log "Installing site dependencies (pnpm)..."
cd "$PROJECT_ROOT/site"
pnpm install
ok "Site dependencies installed"

cd "$PROJECT_ROOT"

log "Installing git hooks (lefthook)..."
lefthook install
ok "Git hooks installed"

log "Allowing direnv for this project..."
direnv allow "$PROJECT_ROOT/.envrc"
ok "direnv allowed"

# ── Done ──────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}✓ Setup complete!${NC}"
echo -e "  Run ${BOLD}just${NC} to see available tasks."
if [[ -n "$SHELL_RC" ]]; then
    echo -e "  ${YELLOW}Restart your terminal (or run: source $SHELL_RC) to activate shell changes.${NC}"
fi
echo ""
