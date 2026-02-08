#!/bin/bash
set -euo pipefail

# S4-09: Diff two packs based on MANIFEST.tsv
# Usage: ops/diff_pack.sh <pack_A> <pack_B>

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <pack_A_dir_or_tar> <pack_B_dir_or_tar>"
    exit 1
fi

PACK_A="$1"
PACK_B="$2"

tmp_base=$(mktemp -d)
trap 'rm -rf "$tmp_base"' EXIT

extract() {
    local src="$1"
    local name="$2"
    local dst="$tmp_base/$name"
    mkdir -p "$dst"
    if [[ "$src" == *.tar.gz ]]; then
        tar -xzf "$src" -C "$dst"
        # If single directory inside, move up
        if [ $(ls "$dst" | wc -l) -eq 1 ] && [ -d "$dst/$(ls "$dst")" ]; then
            mv "$dst/$(ls "$dst")"/* "$dst/"
        fi
    elif [ -d "$src" ]; then
        cp -R "$src/"* "$dst/"
    else
        echo "Error: $src is neither directory nor tar.gz" >&2
        exit 1
    fi
}

echo "Extracting A..."
extract "$PACK_A" "A"
echo "Extracting B..."
extract "$PACK_B" "B"

echo "=== Diff (MANIFEST.tsv) ==="
if [ ! -f "$tmp_base/A/MANIFEST.tsv" ] || [ ! -f "$tmp_base/B/MANIFEST.tsv" ]; then
    echo "Error: MANIFEST.tsv missing in one or both packs."
    exit 1
fi

# Compare MANIFEST.tsv content (ignoring the path column? No, we want full diff)
# MANIFEST columns: path sha256 bytes
# We can diff sorted manifests.
diff -u "$tmp_base/A/MANIFEST.tsv" "$tmp_base/B/MANIFEST.tsv" || true

echo "=== Diff (Files) ==="
# Only meaningful if manifests differ or for extra detail
# but MANIFEST diff is usually enough for S4 goal "What changed?"
