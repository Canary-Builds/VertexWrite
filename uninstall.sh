#!/usr/bin/env bash
set -euo pipefail

HICOLOR="${HOME}/.local/share/icons/hicolor"

rm -f "${HOME}/.local/bin/vertexwrite"
rm -f "${HOME}/.local/bin/vertexmarkdown"
rm -f "${HOME}/.local/bin/markview"
rm -f "${HOME}/.local/share/applications/vertexwrite.desktop"
rm -f "${HOME}/.local/share/applications/vertexmarkdown.desktop"
rm -f "${HOME}/.local/share/applications/markview.desktop"
for size in 16 32 48 64 128 256 512; do
  rm -f "${HICOLOR}/${size}x${size}/apps/vertexwrite.png"
  rm -f "${HICOLOR}/${size}x${size}/apps/vertexmarkdown.png"
  rm -f "${HICOLOR}/${size}x${size}/apps/markview.png"
done

command -v update-desktop-database >/dev/null && \
  update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null && \
  gtk-update-icon-cache -f -t "${HICOLOR}" >/dev/null 2>&1 || true

echo "VertexWrite uninstalled. Source folder is untouched."
