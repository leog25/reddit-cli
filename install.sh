#!/usr/bin/env bash
# Install reddit-cli binary.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/leog25/reddit-cli-releases/main/install.sh | bash
#
# Options (via environment variables):
#   GITHUB_TOKEN  - Required for private repos
#   VERSION       - Pin to a specific tag (e.g. v0.3.0). Default: latest
#   INSTALL_DIR   - Override install path. Default: ~/.local/bin
#   REPO          - Override repo. Default: leog25/reddit-cli
set -euo pipefail

REPO="${REPO:-leog25/reddit-cli}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
VERSION="${VERSION:-latest}"

# ── Detect platform ──────────────────────────────────────────────────

OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Linux)   PLATFORM="linux";;
  Darwin)  PLATFORM="macos";;
  *)       echo "Error: unsupported OS: $OS"; exit 1;;
esac

case "$ARCH" in
  x86_64|amd64)   ARCH_LABEL="x64";;
  aarch64|arm64)   ARCH_LABEL="arm64";;
  *)               echo "Error: unsupported architecture: $ARCH"; exit 1;;
esac

ARTIFACT="reddit-${PLATFORM}-${ARCH_LABEL}"
echo "Detected: ${PLATFORM} ${ARCH_LABEL}"

# ── Auth headers (required for private repos) ────────────────────────

AUTH_HEADER=""
if [ -n "${GITHUB_TOKEN:-}" ]; then
  AUTH_HEADER="Authorization: token ${GITHUB_TOKEN}"
fi

curl_auth() {
  if [ -n "$AUTH_HEADER" ]; then
    curl -fsSL -H "$AUTH_HEADER" "$@"
  else
    curl -fsSL "$@"
  fi
}

# ── Resolve download URL ─────────────────────────────────────────────

if [ "$VERSION" = "latest" ]; then
  echo "Resolving latest release..."
  RELEASE_URL="https://api.github.com/repos/${REPO}/releases/latest"
  TAG="$(curl_auth "$RELEASE_URL" | grep '"tag_name"' | head -1 | sed 's/.*: "\(.*\)".*/\1/')"
  if [ -z "$TAG" ]; then
    echo "Error: could not resolve latest release."
    echo "  - If this is a private repo, set GITHUB_TOKEN"
    exit 1
  fi
  echo "Latest release: $TAG"
else
  TAG="$VERSION"
fi

DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}/${ARTIFACT}"

# GitHub private repo assets need the API + Accept header
if [ -n "${GITHUB_TOKEN:-}" ]; then
  # Get the asset download URL via API
  ASSETS_URL="https://api.github.com/repos/${REPO}/releases/tags/${TAG}"
  ASSET_API_URL="$(curl_auth "$ASSETS_URL" \
    | grep -B3 "\"name\": \"${ARTIFACT}\"" \
    | grep '"url"' | head -1 \
    | sed 's/.*"\(https[^"]*\)".*/\1/')"
  if [ -n "$ASSET_API_URL" ]; then
    DOWNLOAD_CMD="curl -fsSL -H '$AUTH_HEADER' -H 'Accept: application/octet-stream' '$ASSET_API_URL'"
  else
    DOWNLOAD_CMD="curl_auth '$DOWNLOAD_URL'"
  fi
else
  DOWNLOAD_CMD="curl -fsSL '$DOWNLOAD_URL'"
fi

# ── Download & install ────────────────────────────────────────────────

mkdir -p "$INSTALL_DIR"
DEST="${INSTALL_DIR}/reddit"

echo "Downloading ${ARTIFACT} -> ${DEST}..."

if [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${ASSET_API_URL:-}" ]; then
  curl -fsSL -H "$AUTH_HEADER" -H "Accept: application/octet-stream" "$ASSET_API_URL" -o "$DEST"
else
  curl_auth "$DOWNLOAD_URL" -o "$DEST"
fi

chmod +x "$DEST"

# ── Verify ────────────────────────────────────────────────────────────

if "$DEST" --help > /dev/null 2>&1; then
  echo "Installed reddit to ${DEST}"
else
  echo "Error: binary failed smoke test"
  rm -f "$DEST"
  exit 1
fi

# ── PATH check ────────────────────────────────────────────────────────

if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
  echo ""
  echo "Add to your PATH by adding this to your shell profile:"
  echo ""
  SHELL_NAME="$(basename "${SHELL:-/bin/bash}")"
  case "$SHELL_NAME" in
    zsh)  echo "  echo 'export PATH=\"${INSTALL_DIR}:\$PATH\"' >> ~/.zshrc && source ~/.zshrc";;
    fish) echo "  fish_add_path ${INSTALL_DIR}";;
    *)    echo "  echo 'export PATH=\"${INSTALL_DIR}:\$PATH\"' >> ~/.bashrc && source ~/.bashrc";;
  esac
fi
