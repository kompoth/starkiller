#~/bin/bash
set -e

uv run --no-sync bump-my-version bump ${1}

NEW_VERSION=$(uv run --no-sync bump-my-version show current_version)
echo "Publishing v${NEW_VERSION}"

uv build
uv publish
