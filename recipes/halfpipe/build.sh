#!/bin/bash
# shellcheck disable=SC2154
export SETUPTOOLS_SCM_PRETEND_VERSION="${halfpipe_version}"

# Fetch the git-annex branch from the source repo
git remote set-url origin "$(realpath "${RECIPE_DIR}/../..")"
git fetch origin git-annex:git-annex
git annex init

# Setup hardlinking to pull directly from your local host repo
git config annex.thin true
git config annex.hardlink true

# Unlock and fetch the data
git annex unlock src
git annex get src --from=origin

"${PYTHON}" -m pip install --default-timeout=100 . --no-deps -v
