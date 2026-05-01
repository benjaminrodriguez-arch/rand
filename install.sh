#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="$HOME/.rand-self"
BIN="/usr/local/bin/rand"

echo "Installing rand..."
mkdir -p "$STATE_DIR"

# Shuffle and activate bundled US addresses
if [[ -f "$SCRIPT_DIR/data/us.txt" ]]; then
  echo "  Activating US addresses..."
  python3 -c "
import random
lines = open('$SCRIPT_DIR/data/us.txt').readlines()
random.shuffle(lines)
open('$STATE_DIR/us_data.txt', 'w').writelines(lines)
"
  echo "1" > "$STATE_DIR/us_ptr"
fi

# Decompress and shuffle reserve bundles for all other countries
for src in "$SCRIPT_DIR/data"/*.txt.gz; do
  [[ -f "$src" ]] || continue
  cc=$(basename "$src" .txt.gz)
  reserve="$STATE_DIR/${cc}_reserve.txt"
  echo "  Installing reserve for $(echo "$cc" | tr '[:lower:]' '[:upper:]')..."
  python3 -c "
import gzip, random
lines = gzip.open('$src', 'rt', encoding='utf-8').readlines()
random.shuffle(lines)
open('$reserve', 'w').writelines(lines)
"
done

# Install rand binary
sudo cp "$SCRIPT_DIR/rand" "$BIN"
sudo chmod +x "$BIN"

echo ""
echo "rand is ready."
echo ""
echo "  rand              US address (ready now)"
echo "  rand -list        See all 29 supported countries"
echo "  rand -download de 100   Activate Germany (instant, no internet)"
echo "  rand -download au 100   Activate Australia (instant, no internet)"
