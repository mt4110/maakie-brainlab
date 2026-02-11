# Walkthrough: S8-00 Governance Layer v1

## 目的

S8-00 の governance layer v1 を「迷子ゼロ」で動かす。

## 1. ローカル (Permissive)

デフォルトは **Permissive** (壊さない) モードです。Policy ファイルが存在しなくても、あるいは違反があっても、検証エラーにはなりません（警告のみ）。

```bash
cd "$(git rev-parse --show-toplevel)"

# 通常のテスト
go test ./...

# Verify 実行 (Policy Mode = local/permissive)
# 既存の証跡がある場合:
LATEST=$(ls -t .local/evidence_store/packs/*/*.tar.gz | head -n 1)
go run ./cmd/evidencepack verify --pack "$LATEST"
```

**期待される挙動:**

- Policy が無くても動作する。
- 署名が無い場合でも Pass する (v1 default)。
- Policy 違反があっても fail しない (警告ログが出る場合がある)。

## 2. CI (Strict)

CI 環境 (または `REVIEWPACK_POLICY_MODE=ci`) では **Strict** (統治) モードになります。

```bash
export REVIEWPACK_POLICY_MODE=ci

# Verify 実行
go run ./cmd/evidencepack verify --pack "$LATEST"
```

**期待される挙動:**

- Policy ファイル (`ops/reviewpack_policy.toml`) のロードに失敗した場合 → **Fail**
- **署名が存在する場合**: KeyID が allowlist (`ops/reviewpack_policy.toml` の `keys.allowed_key_ids`) に無ければ **Fail**
- **署名が存在しない場合**: `require_signature_in_ci = true` なら **Fail** (v1デフォルトはfalse)

## 3. 失敗時の復旧 (1スクロール復旧)

エラーメッセージには以下が表示されます:

- Mode (ci/local)
- 違反した Policy 項目
- 次のアクション

### 例: Key Rejected

```text
POLICY VIOLATION (v1 defined in ops/reviewpack_policy.toml)
Mode: strict (Environment: ci)
Error: policy violation: key ... is not in allowed_key_ids

ACTION REQUIRED:
3. If key rejected: Add KeyID ... to 'allowed_key_ids' in policy
```

**対応:**

`ops/reviewpack_policy.toml` を編集し、Trusted Key ID を追加してください。

```toml
[keys]
allowed_key_ids = ["EXISTING_KEY", "NEW_KEY_ID"]
```
