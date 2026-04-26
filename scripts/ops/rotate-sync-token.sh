#!/usr/bin/env bash
#
# Rotate the SYNC_TOKEN GitHub Actions secret from 1Password.
#
# The upstream sync workflow (.github/workflows/sync-upstream.yml) needs a PAT
# with `Contents`, `Pull requests`, and `Workflows` = read & write to push
# branches that touch .github/workflows/*. We keep the PAT in 1Password —
# never in plaintext on disk — and ship it to GitHub via this script.
#
# Usage:
#   ./scripts/ops/rotate-sync-token.sh
#
# Prerequisites:
#   - 1Password CLI signed in (Touch ID / desktop integration)
#   - gh CLI authenticated as a user with admin on liberathio/hermes-agent
#   - 1P item titled "GitHub PAT — hermes-agent SYNC_TOKEN" in vault Personal,
#     with the PAT in the `credential` field.
#
# To create the 1P item the first time, generate a fine-grained PAT at
#   https://github.com/settings/personal-access-tokens
# scoped to liberathio/hermes-agent with the three permissions above, then:
#   op item edit "GitHub PAT — hermes-agent SYNC_TOKEN" credential="<paste>"

set -euo pipefail

REPO="${REPO:-liberathio/hermes-agent}"
OP_ITEM="${OP_ITEM:-GitHub PAT — hermes-agent SYNC_TOKEN}"
OP_VAULT="${OP_VAULT:-Personal}"
SECRET_NAME="${SECRET_NAME:-SYNC_TOKEN}"

if ! command -v op >/dev/null; then
  echo "error: 1Password CLI (op) not installed — brew install --cask 1password-cli" >&2
  exit 1
fi

if ! command -v gh >/dev/null; then
  echo "error: GitHub CLI (gh) not installed — brew install gh" >&2
  exit 1
fi

# Note: we don't gate on `op whoami` — with the macOS desktop integration
# (Touch ID / app authentication), `op whoami` returns "not signed in"
# even when `op item get` works fine via biometrics. We rely on the actual
# `op item get` call below to surface auth errors.

token="$(op item get "${OP_ITEM}" --vault "${OP_VAULT}" --reveal --fields credential 2>/dev/null || true)"
if [ -z "${token}" ]; then
  echo "error: could not read ${OP_ITEM} from 1Password — make sure the desktop app is unlocked and CLI integration is enabled (Settings → Developer)" >&2
  exit 1
fi
if [ "${token}" = "placeholder-rotate-me" ]; then
  echo "error: ${OP_ITEM} still has the placeholder credential — paste the real PAT into 1Password first" >&2
  exit 1
fi

printf '%s' "${token}" | gh secret set "${SECRET_NAME}" --repo "${REPO}"
echo "✓ ${SECRET_NAME} updated on ${REPO} from 1Password (${OP_ITEM})"
