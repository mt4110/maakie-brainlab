# AI Text Guard Constitution

This document defines the **Non-negotiable Rules** for AI-generated text in this repository.
The goal is to strictly prevent local file URLs and absolute paths from leaking into documentation, PR descriptions, and logs.

## 1. Prohibited Patterns (Strictly Forbidden)

AI must **NEVER** generate text that completes the following patterns in **any** output (docs, PR body, comments, examples, logs).

### 1.1 File URL Format
*   **Forbidden**: `file` + `://` followed by any path.
*   **Detection**: `bash ops/finalize_clean.sh --check`
*   **Why**: It leaks local environment paths and breaks portability.

### 1.2 Absolute Paths
*   **Forbidden**: Paths starting with `/Users/...`, `/home/...`, or similar user-specific roots as **links**.
*   **Why**: It is specific to the machine and irrelevant to the project.

## 2. Recommended Alternatives

### 2.1 Relative Paths
Always use repo-root relative paths enclosed in backticks.
*   **Good**: \`docs/rules/AI_TEXT_GUARD.md\`
*   **Bad**: `[AI_TEXT_GUARD.md](file[:]///Users/me/repo/docs/rules/AI_TEXT_GUARD.md)`

### 2.2 Describing Forbidden Patterns
If you must explain the forbidden pattern itself, **break the prohibited sequence** or use a placeholder.
*   **Good**: "`file:` scheme", "<FILE_URL>"
*   **Bad**: (Do not write the example here as it would violate the rule)

## 3. Mandatory AI Prompt Block

When requesting work from an AI, **ALWAYS** paste this block at the top of your prompt.

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0) 憲法（Non-negotiable / 絶対遵守）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

C0. 禁止（出力・docs・PR本文・例文・walkthrough・コメント等、あらゆるテキストで禁止）
- matches: `file` + `://` (file URL形式)
- matches: `/Users/...` as link

C1. 代替（必須）
- ファイル参照はリンクにせず、必ず `相対パス` をバッククォートで囲む
  例: `.github/workflows/run_always_1h.yml`
- 禁止対象を説明する必要がある場合は、分割表記またはプレースホルダで書く
  例: `file:` + `//`、または `<FILE_URL>` のように置換する

C2. 最終提出前セルフチェック（必須）
- 提出直前に以下を実行し、ヒットしたら該当箇所を分割表記/プレースホルダへ置換し、再チェックする
  - `bash ops/finalize_clean.sh --check`
  - 自動修正には `bash ops/finalize_clean.sh --fix` を使用可能（※差分を必ず確認すること）
  - 近接する `//` との組み合わせが “成立していないか” を目視確認する（成立する書き方は禁止）
```

## 4. Self-Correction Procedure

Before submitting any changes, run the following check locally:

```bash
# Check for "file:" occurrences in key directories
bash ops/finalize_clean.sh --check
```

If detection fails:

```bash
# Auto-fix text files
bash ops/finalize_clean.sh --fix
```

If any hits form a valid file URL, **fix them immediately** by using backticks or breaking the string.
