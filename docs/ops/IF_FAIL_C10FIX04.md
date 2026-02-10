# IF_FAIL_C10FIX04 — File URL Guard Fix / check-doc-links Recovery

目的：`make check-doc-links`（file: // リンク禁止チェック）が **迷子にならず復帰できる**ようにする。  
重要：このリポジトリのガードは **コードブロックも含めて**文字列パターンで検出するため、ドキュメント内に **`file:` と `//` が連続した形**を置かないこと（＝生の file URL 文字列を置かない）。

---

## 0) 最初にやること（迷子防止・10秒）

```bash
cd "$(git rev-parse --show-toplevel)"
pwd
git rev-parse --short HEAD
```

---

## 1) 症状別の復帰ルート

### S1: `make check-doc-links` が WARN を出す / “OKなのに変” / targets が出ない

期待挙動：

* `[INFO] targets:` が必ず出る
* `file:` と `//` が連続する “リンク形式” が1件でもあれば **必ずFAIL**
* `task.md / implementation_plan.md missing` のような **存在しない required 警告は出ない**

復帰手順：

```bash
bash -x ops/check_no_file_url.sh | sed -n '1,120p'
```

確認：

```bash
grep -n "check-doc-links" -n Makefile
sed -n '1,200p' ops/check_no_file_url.sh
```

---

### S2: `[FAIL] Forbidden file: // link(s) found:` が出て止まる（正常）

これは **正しい停止**。直すのは “file: と // が連続するリンク形式” だけ。

```bash
make check-doc-links || true
```

表示された `path:line:` の箇所を修正。原則：

* `[...] (file: と // が連続する形 ...)` → **repo相対パス**にする（例：`docs/ops/xxx.md`）
* `<file: と // が連続する形 ...>` → **repo相対パス**にする

修正後：

```bash
make check-doc-links
```

---

### S3: `fatal: .git/index: ... Operation not permitted`（Gitが死ぬ）

iCloud配下 / Sandbox / TCC（macOS権限）が原因になりやすい。repo本体は iCloud 外に置く。

確認：

```bash
pwd
ls -ld .git .git/index
```

移設例（必要時）：

```bash
OLD="$HOME/Library/Mobile Documents/com~apple~CloudDocs/maakie-brainlab"
NEW="$HOME/dev/maakie-brainlab"
mkdir -p "$HOME/dev"
rsync -aH --progress "$OLD/" "$NEW/"
cd "$NEW"
git status --porcelain
```

---

### S4: “止まってるっぽいけどログが出ない”（実は正常）

`git diff > file` は成功しても無言が正常。可視化したい場合：

```bash
mkdir -p .local/reviewpack_artifacts
echo "[INFO] writing diff..."
git diff -- Makefile ops/check_no_file_url.sh \
  | tee .local/reviewpack_artifacts/diff_check-doc-links.txt >/dev/null
echo "[OK] wrote diff"
```

---

## 2) “確実に効いてる”証拠（ネガティブテスト）

このドキュメント内に生の file:+// 連続を置かないため、シェル連結で実行時に禁止パターンを生成する。

```bash
printf '%s\n' '[x](file:'"///tmp/evil"')' > docs/.tmp_file_url_check.md
make check-doc-links && { echo "BUG: should have failed"; exit 1; } || true
rm -f docs/.tmp_file_url_check.md
git status --porcelain
```

---

## 3) 最終チェック（完了条件）

```bash
make check-doc-links
git status --porcelain
```

PASS と clean で完了。
