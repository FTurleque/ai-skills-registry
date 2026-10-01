#!/usr/bin/env bash
# Installation du superviseur de code (Linux / macOS).
#   ./install.sh              installation globale (~/.claude)
#   ./install.sh --uninstall  desinstallation
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
py="$(command -v python3 || command -v python || true)"
if [ -z "$py" ]; then
  echo "Python 3 est introuvable. Installe-le puis relance." >&2
  exit 1
fi
exec "$py" "$here/install.py" "$@"
