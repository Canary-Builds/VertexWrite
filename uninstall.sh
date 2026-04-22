#!/usr/bin/env bash
set -euo pipefail

HICOLOR="${HOME}/.local/share/icons/hicolor"

rm -f "${HOME}/.local/bin/vertexmarkdown"
rm -f "${HOME}/.local/share/applications/vertexmarkdown.desktop"
for size in 16 32 48 64 128 256 512; do
  rm -f "${HICOLOR}/${size}x${size}/apps/vertexmarkdown.png"
done

command -v update-desktop-database >/dev/null && \
  update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null && \
  gtk-update-icon-cache -f -t "${HICOLOR}" >/dev/null 2>&1 || true

echo "VertexMarkdown uninstalled. Source folder is untouched."

