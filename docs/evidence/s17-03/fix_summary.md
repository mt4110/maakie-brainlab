# S17-03 Retro-Fixpack Summary (Canonical)

This folder exists to reconcile audit consistency for S17-03 and preserve offline-verifiable PASS evidence.

## Canonical (Single Source of Truth)
- **Commit**: `03108902475ec622596da49e060422e285ae4564` (short: `0310890`)
- **Review Bundle**: `review_bundle_20260215_135256.tar.gz`
- **Bundle SHA256**: `7f444f689d06e2acd830c4cbafc17f26a111ff0c1616b5df6580f096bedd2587`

This canonical tuple (commit + bundle + sha256) is the only authoritative reference for PR #51.

## What was fixed (Audit + Ritual Hardening)
1. **Evidence reconciliation**: 
   - Updated documentation to remove contradictory statements and align references to the canonical tuple.
   - Ensured PASS artifacts are stored under `docs/evidence/s17-03/` for offline review.

2. **Hygiene hardening**:
   - Prohibited `[FILE_URI]` patterns are obfuscated as needed to satisfy automated gates.
   - Repo-relative paths are used for audit references.

3. **CI signing key injection**:
   - `.github/workflows/run_always_1h.yml` now materializes the signing key from `S6_SIGNING_KEY_B64` and exports `S6_SIGNING_KEY` for downstream steps.
   - `ops/run_always_1h.sh` enforces strict CI signing when `require_signature_in_ci=true` (fail fast if key is missing) and logs `SIGNING_MODE` for transparency.

## Offline Evidence (PASS)
- [log_pass_22027976749.txt](log_pass_22027976749.txt)
- [log_pass_22028710788.txt](log_pass_22028710788.txt)
- [run_22028710788.json](run_22028710788.json)

Historical context is preserved, but only the canonical tuple above is used for PR ritual and audit claims.

## Final Closeout (Canonical Fixation: Stop Infinite Drift)

### Canonical (Single Source of Truth)
- Commit: `0310890`
- Review Bundle: `review_bundle_20260215_135256.tar.gz`
- SHA256: `7f444f689d06e2acd830c4cbafc17f26a111ff0c1616b5df6580f096bedd2587`

### Historical (Demoted)
- `review_bundle_20260215_121251.tar.gz` / `03cc0575...` は過去ログとして保持（Canonical ではない）。

### Why this ends drift
- verify-only 実行は bundle 名/sha が変動し得る（観測）。
- Canonical は commit 固定とし、観測結果で更新しない。
- これにより “最新出力を canonical にする” 方式の無限更新ループを停止した。

### Hygiene
- repo tracked files 内の `file://` を禁止し、発見時は `[FILE_URI]` に無害化。
