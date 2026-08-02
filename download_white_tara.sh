#!/usr/bin/env bash
# Download Ghostism's White Tara (CC-BY) via Sketchfab Download API into this RCP package.
set -euo pipefail

MODEL_UID="9b8e13a8b1d24034bd57a0a781e66967"
OUT_DIR="$(cd "$(dirname "$0")" && pwd)/Sources/White Tara/White Tara.rkassets/Models"
mkdir -p "$OUT_DIR"

if [[ -z "${SKETCHFAB_API_TOKEN:-}" ]]; then
  echo "Set SKETCHFAB_API_TOKEN first."
  echo "  1. Open https://sketchfab.com/settings/password"
  echo "  2. Copy your API Token"
  echo "  3. Run:  export SKETCHFAB_API_TOKEN='paste-here'"
  echo "  4. Re-run this script"
  exit 1
fi

echo "Requesting download URLs for White Tara ($MODEL_UID)..."
RESP=$(curl -sS "https://api.sketchfab.com/v3/models/${MODEL_UID}/download" \
  -H "Authorization: Token ${SKETCHFAB_API_TOKEN}")

if echo "$RESP" | grep -q '"detail"'; then
  echo "API error:"
  echo "$RESP"
  exit 1
fi

USDZ_URL=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usdz",{}).get("url",""))' <<<"$RESP")
GLTF_URL=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("gltf",{}).get("url",""))' <<<"$RESP")
GLB_URL=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("glb",{}).get("url",""))' <<<"$RESP")

if [[ -n "$USDZ_URL" ]]; then
  echo "Downloading USDZ (best for Reality Composer Pro)..."
  curl -L --fail --progress-bar "$USDZ_URL" -o "$OUT_DIR/White_Tara.usdz"
  echo "Saved: $OUT_DIR/White_Tara.usdz"
elif [[ -n "$GLB_URL" ]]; then
  echo "No USDZ; downloading GLB..."
  curl -L --fail --progress-bar "$GLB_URL" -o "$OUT_DIR/White_Tara.glb"
  echo "Saved: $OUT_DIR/White_Tara.glb"
elif [[ -n "$GLTF_URL" ]]; then
  echo "No USDZ/GLB; downloading glTF zip..."
  curl -L --fail --progress-bar "$GLTF_URL" -o "$OUT_DIR/White_Tara_gltf.zip"
  unzip -o "$OUT_DIR/White_Tara_gltf.zip" -d "$OUT_DIR/White_Tara_gltf"
  echo "Saved glTF under $OUT_DIR/White_Tara_gltf"
else
  echo "No downloadable formats in response:"
  echo "$RESP"
  exit 1
fi

# Attribution file (CC-BY requires credit)
cat > "$OUT_DIR/CREDITS.txt" << 'CREDIT'
White Tara
Author: Ghostism (https://sketchfab.com/Ghostism)
Source: https://sketchfab.com/3d-models/white-tara-9b8e13a8b1d24034bd57a0a781e66967
License: CC Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/)
CREDIT

ls -lh "$OUT_DIR"
echo "Done. In Reality Composer Pro: File → Import (or drag White_Tara.usdz into the scene)."
