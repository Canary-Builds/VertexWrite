#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <series> <ppa-revision>"
  echo "Example: $0 noble 1"
  exit 1
fi

SERIES="$1"
REV="$2"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v dch >/dev/null; then
  echo "dch not found. Install devscripts first."
  exit 1
fi

UPSTREAM_VERSION="$(python3 vertexwrite.py -V | awk '{print $2}')"
PKG_VERSION="${UPSTREAM_VERSION}+${SERIES}${REV}"

# Use -b to allow per-series version lanes (e.g. jammy1 after noble4 in changelog history).
dch -b --distribution "$SERIES" --newversion "$PKG_VERSION" "PPA upload for $SERIES"

dpkg-buildpackage -S -sa

CHANGES="../vertexwrite_${PKG_VERSION}_source.changes"
echo "Built source package: ${CHANGES}"
echo "Upload with: dput ppa:<launchpad-user>/<ppa-name> ${CHANGES}"
