#!/usr/bin/env bash
# Compila, arma Spoke.app, la firma y la instala en ~/Applications.
#   ./build.sh          compila e instala
#   ./build.sh --run    además la (re)abre
set -euo pipefail
cd "$(dirname "$0")"

APP="build/Spoke.app"
DEST="$HOME/Applications/Spoke.app"
# Certificado local autofirmado: mantiene los permisos (micrófono,
# accesibilidad) entre recompilaciones. Si no existe, firma ad-hoc.
IDENTITY="Spoke Local Signing"

swift build -c release
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp .build/release/Spoke "$APP/Contents/MacOS/Spoke"
cp Resources/Info.plist "$APP/Contents/Info.plist"
cp Resources/AppIcon.icns Resources/MenuBarIcon.png Resources/MenuBarIcon@2x.png "$APP/Contents/Resources/"

if security find-identity -p codesigning | grep -q "$IDENTITY"; then
  codesign --force --sign "$IDENTITY" "$APP"
else
  echo "⚠️  Sin certificado '$IDENTITY': firma ad-hoc (los permisos se pierden al recompilar)"
  codesign --force --sign - "$APP"
fi

pkill -x Spoke 2>/dev/null && while pgrep -x Spoke >/dev/null; do sleep 0.1; done || true
mkdir -p "$HOME/Applications"
rm -rf "$DEST"
cp -R "$APP" "$DEST"
echo "✅ Instalado en $DEST"

if [[ "${1:-}" == "--run" ]]; then open "$DEST"; fi
