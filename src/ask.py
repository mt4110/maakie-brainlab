#!/usr/bin/env python3
import argparse
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional at runtime
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    load_dotenv(ROOT / ".env", override=False)

def normalize_rag_blocks(out: str) -> str:
    """
    LLM出力が崩れても eval が安定して解析できるように、
    4ブロック（結論/根拠/参照/不確実性）を最低限の箇条書き形式へ正規化する。
    """
    headers = {"結論:", "根拠:", "参照:", "不確実性:"}
    lines = out.splitlines()

    def is_header(line: str) -> bool:
        return line.strip() in headers

    # 結論: の直後1行は必ず "- ..." にする（最初の非空行だけ）
    for i, line in enumerate(lines):
        if line.strip() == "結論:":
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and not is_header(lines[j]):
                if not lines[j].lstrip().startswith("-"):
                    lines[j] = "- " + lines[j].strip()
            break

    # 根拠/参照/不確実性: は、ブロック内の非空行をすべて "- ..." に揃える
    for h in ("根拠:", "参照:", "不確実性:"):
        try:
            i = next(idx for idx, line in enumerate(lines) if line.strip() == h)
        except StopIteration:
            continue
        k = i + 1
        while k < len(lines) and not is_header(lines[k]):
            t = lines[k].strip()
            if t and not t.startswith("-") and not t.startswith("---"):
                lines[k] = "- " + t
            k += 1

    return "\n".join(lines)

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def build_unknown() -> str:
    return "\n".join(
        [
            "結論:",
            "- 不明（参照できる根拠が見つかりませんでした）",
            "",
            "根拠:",
            "- 不明（CONTEXTが空）",
            "",
            "参照:",
            "- 不明（参照なし）",
            "",
            "不確実性:",
            "- 質問に答えるための資料が data/raw/ に存在しない可能性があります",
        ]
    )


def extract_terms(question: str) -> list[str]:
    """
    FTS検索用のquery term抽出（決定論・軽量）
    - ファイル名 / 英数字 / 日本語（かなカナ漢字の連続）を拾う
    - 日本語は「〜について/とは/を/は...」等で topic 部分に寄せる
    """
    q = question or ""

    # 日本語 stop（ノイズ化しやすい語）
    jp_stop = {
        "これ", "それ", "あれ", "ここ", "そこ", "どこ",
        "なに", "何", "です", "ます", "ください", "下さい",
        "教えて", "お願いします", "要点", "存在", "教えてください",
    }

    # 「topic の後ろに付く」ことが多い接尾句（ここで切る）
    jp_suffixes = ["について", "とは", "に関して", "を教えて", "を教えてください"]
    # さらに細かい粒度に落とすための区切り（最初に出たところで切る）
    jp_seps = ["を", "に", "で", "が", "は", "の", "と", "へ", "から", "まで", "や", "も", "か"]

    def _jp_topic(token: str) -> str:
        s = token.strip(" 　\t\r\n")
        if not s:
            return ""
        # 冒頭の指示語は落とす（「この知識ベース」→「知識ベース」など）
        for pre in ("この", "その", "あの"):
            if s.startswith(pre) and len(s) > len(pre) + 1:
                s = s[len(pre):]
                break
        # まずは「について/とは...」系で前半に寄せる
        for suf in jp_suffixes:
            idx = s.find(suf)
            if idx > 0:
                s = s[:idx]
        # 次に助詞・区切りでtopicを短くする（最初の出現位置）
        cut = len(s)
        for sep in jp_seps:
            idx = s.find(sep)
            if idx > 0 and idx < cut:
                cut = idx
        s = s[:cut].strip()
        # 記号を軽く落とす
        s = s.strip("？?！!。．，,・「」『』（）()[]【】")
        return s

    def _split_jp(token: str) -> list[str]:
        # セパレータで分割して複数の単語として拾う
        pattern = f"({'|'.join(re.escape(s) for s in jp_seps)})"
        parts = re.split(pattern, token)
        res = []
        for p in parts:
            if not p:
                continue
            # セパレータ自体は無視
            if p in jp_seps:
                continue
            t = _jp_topic(p)
            if len(t) >= 2 and t not in jp_stop:
                res.append(t)
        return res

    # candidates: (priority, pos, token)
    # priority: 0=file, 1=ascii, 2=jp
    cands: list[tuple[int, int, str]] = []

    # 1) hello.md のような “ファイルっぽい” token を優先
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_-]*\.[A-Za-z0-9]+", q):
        f = m.group(0)
        base = f.split(".", 1)[0]
        if len(base) >= 2:
            cands.append((0, m.start(), base))

    # 2) 英数字ワード（長め優先）
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_-]+", q):
        w = m.group(0)
        if w.lower() in {"http", "https"}:
            continue
        if len(w) >= 3:
            cands.append((1, m.start(), w))

    # 3) 日本語ワード（かな/カナ/漢字の連続）
    for m in re.finditer(r"[ぁ-んァ-ンー一-龯]{2,}", q):
        raw = m.group(0)
        # 長い連結（AとBのC）を分解
        sub_tokens = _split_jp(raw)
        for tok in sub_tokens:
             cands.append((2, m.start(), tok))

    # 優先度→出現順でソートし、ユニーク化（順序保持）
    cands.sort(key=lambda x: (x[0], x[1]))
    seen: set[str] = set()
    out: list[str] = []
    for _, _, t in cands:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= 5:
            break
    return out


def to_fts_or_query(terms: list[str]) -> str:
    # FTS5 の構文エラー回避：各termを "..." で囲い OR 連結
    # ダブルクォートは二重化でエスケープ
    safe = [t.replace('"', '""') for t in terms if t.strip()]
    return " OR ".join(f'"{t}"' for t in safe)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def chat_completion_url_candidates(base_url: str) -> list[str]:
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        raw = "http://127.0.0.1:11434/v1"

    if raw.endswith("/chat/completions"):
        raw = raw[: -len("/chat/completions")].rstrip("/")

    candidates = [f"{raw}/chat/completions"]
    if raw.endswith("/v1"):
        root = raw[: -len("/v1")].rstrip("/")
        if root:
            candidates.append(f"{root}/chat/completions")
    else:
        candidates.append(f"{raw}/v1/chat/completions")

    return _dedupe_keep_order([c for c in candidates if c.strip()])


def _truncate_line(text: str, limit: int = 220) -> str:
    one = " ".join((text or "").split())
    if len(one) <= limit:
        return one
    return one[:limit].rstrip() + "..."


def chat_openai_compat(
    base_url: str, model: str, messages, temperature: float = 0.2
) -> str:
    payload = {"model": model, "messages": messages, "temperature": temperature}
    headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'dummy')}"}
    attempts: list[str] = []

    for url in chat_completion_url_candidates(base_url):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=180)
        except requests.RequestException as exc:
            attempts.append(f"{url} -> network_error: {_truncate_line(str(exc), 140)}")
            continue

        if r.status_code == 404:
            attempts.append(f"{url} -> 404")
            continue

        try:
            r.raise_for_status()
        except requests.HTTPError as exc:
            detail = _truncate_line(r.text, 180)
            raise RuntimeError(
                f"local model api error status={r.status_code} url={url} detail={detail}"
            ) from exc

        data: dict[str, Any] = r.json()
        content = (
            (data.get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if isinstance(content, str) and content.strip():
            return content
        raise RuntimeError(f"local model api returned empty content: {url}")

    attempted = "; ".join(attempts) if attempts else "(no attempts)"
    raise RuntimeError(
        "openai-compatible endpoint not found. "
        f"OPENAI_API_BASE={base_url or '(empty)'} tried=[{attempted}]. "
        "Set OPENAI_API_BASE to your LLM server (e.g. http://127.0.0.1:11434/v1)."
    )


def resolve_local_model_backend() -> str:
    raw = os.getenv("LOCAL_MODEL_BACKEND", "openai_compat").strip().lower()
    if raw == "gemma_lab":
        return "gemma_lab"
    return "openai_compat"


def resolve_local_model_name(backend: Optional[str] = None) -> str:
    resolved_backend = backend or resolve_local_model_backend()
    if resolved_backend == "gemma_lab":
        return os.getenv("GEMMA_MODEL_ID", "google/gemma-4-E2B-it").strip() or "google/gemma-4-E2B-it"
    return os.getenv("LOCAL_GGUF_MODEL", "Qwen2.5-7B-Instruct-Q4_K_M.gguf").strip() or "Qwen2.5-7B-Instruct-Q4_K_M.gguf"


def resolve_gemma_lab_root() -> Path:
    raw = os.getenv("GEMMA_LAB_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (ROOT.parent / "gemma-lab").resolve()


def resolve_gemma_lab_python(root: Optional[Path] = None) -> str:
    raw = os.getenv("GEMMA_LAB_PYTHON", "").strip()
    if raw:
        return str(Path(raw).expanduser())
    gemma_root = root or resolve_gemma_lab_root()
    return str(gemma_root / ".venv" / "bin" / "python")


def gemma_lab_bridge_path() -> Path:
    return ROOT / "scripts" / "gemma_lab_bridge.py"


def parse_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("expected JSON object")
    return parsed


def chat_gemma_lab(messages, model: str) -> str:
    gemma_root = resolve_gemma_lab_root()
    python = resolve_gemma_lab_python(gemma_root)
    bridge = gemma_lab_bridge_path()
    if not gemma_root.exists():
        raise RuntimeError(f"gemma-lab root not found: {gemma_root}")
    if os.sep in python and not Path(python).exists():
        raise RuntimeError(f"gemma-lab python not found: {python}")
    if not bridge.exists():
        raise RuntimeError(f"gemma bridge script not found: {bridge}")

    proc = subprocess.run(
        [
            python,
            str(bridge),
            "--mode",
            "chat",
            "--gemma-root",
            str(gemma_root),
            "--model-id",
            model,
        ],
        cwd=str(ROOT),
        input=json.dumps({"model_id": model, "messages": messages}, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=20 * 60,
    )
    payload = parse_json_object(proc.stdout) if proc.stdout.strip() else {}
    if proc.returncode != 0:
        detail = str(payload.get("error") or proc.stderr or proc.stdout).strip()
        raise RuntimeError(detail or f"gemma-lab bridge failed with exit code {proc.returncode}")
    if str(payload.get("status") or "").strip().lower() != "ok":
        detail = str(payload.get("error") or proc.stderr or proc.stdout).strip()
        raise RuntimeError(detail or "gemma-lab bridge did not return ok status")
    content = str(payload.get("output_text") or "").strip()
    if content:
        return content
    raise RuntimeError("gemma-lab returned empty content")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--index-dir", default="index")
    ap.add_argument("--db-name", default="index.sqlite3")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.0)
    args = ap.parse_args()

    db_path = ROOT / args.index_dir / args.db_name
    if not db_path.exists():
        raise SystemExit(f"[ask] index db not found: {db_path}. run build_index first.")

    system_prompt = load_text(ROOT / "prompts" / "system.md")
    rag_format = load_text(ROOT / "prompts" / "rag.md")

    terms = extract_terms(args.question)
    # terms が空なら検索不能なので unknown を返す（誤参照フォールバックはしない）
    if not terms:
        print(build_unknown())
        return
    q = to_fts_or_query(terms)

    conn = sqlite3.connect(str(db_path))
    try:
        rows = []
        if q:
            rows = conn.execute(
                "SELECT path, chunk_index, text, bm25(chunks_fts) AS score "
                "FROM chunks_fts WHERE chunks_fts MATCH ? "
                "ORDER BY score ASC LIMIT ?",
                (q, args.top_k),
            ).fetchall()

        # JPフォールバック：FTSが弱い日本語は LIKE で救う（暴発防止のため日本語termがあるときだけ）
        if not rows:
            jp_terms = [t for t in terms if re.search(r"[ぁ-んァ-ン一-龯]", t)]
            if jp_terms:
                likes = [f"%{t}%" for t in jp_terms]
                where = " OR ".join(["text LIKE ?"] * len(likes))
                rows = conn.execute(
                    "SELECT path, chunk_index, text, 0.0 AS score "
                    f"FROM chunks WHERE {where} "
                    "ORDER BY path ASC, chunk_index ASC LIMIT ?",
                    (*likes, args.top_k),
                ).fetchall()

        # KB要約系だけ最後の保険：各docのchunk-0を集める（決定論）
        if not rows and re.search(r"(知識ベース|ファイル|要約|目的)", args.question):
            rows = conn.execute(
                "SELECT path, chunk_index, text, 0.0 AS score "
                "FROM chunks WHERE chunk_index = 0 "
                "ORDER BY path ASC LIMIT ?",
                (args.top_k,),
            ).fetchall()
    finally:
        conn.close()

    if not rows:
        print(build_unknown())
        return

    sources = []
    context_parts = []
    for path, chunk_index, text, score in rows:
        src = f"{path}#chunk-{chunk_index}"
        sources.append(src)
        context_parts.append(f"[{src} score={score:.3f}]\n{text}\n")

    context = "\n---\n".join(context_parts)

    user_prompt = (
        "CONTEXT:\n"
        f"{context}\n\n"
        "INSTRUCTION:\n"
        "- CONTEXT に基づいて回答してください。CONTEXT外は推測禁止。\n"
        "- 回答は日本語で記述してください。\n"
        "- 根拠はCONTEXTの記述を引用して示してください。\n"
        "- 出力フォーマットは必ず以下に従ってください。\n\n"
        f"{rag_format}\n\n"
        f"QUESTION:\n{args.question}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    backend = resolve_local_model_backend()
    base_url = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11434/v1")
    model = resolve_local_model_name(backend)
    try:
        if backend == "gemma_lab":
            out = chat_gemma_lab(messages, model)
        else:
            out = chat_openai_compat(base_url, model, messages, temperature=args.temperature)
    except Exception as exc:
        refs = "\n".join(f"- {s}" for s in sources) if sources else "- 不明（参照なし）"
        if backend == "gemma_lab":
            uncertainty_lines = [
                "- gemma-lab 実行系の初期化またはモデル読み込みに失敗しました。",
                "- GEMMA_LAB_ROOT / GEMMA_LAB_PYTHON / GEMMA_MODEL_ID を確認してください。",
                "- Hugging Face キャッシュ未配置やメモリ不足でも失敗します。",
            ]
        else:
            uncertainty_lines = [
                "- OPENAI_API_BASE が LLM サーバーを指していない可能性があります。",
                "- 例: http://127.0.0.1:11434/v1",
            ]
        out = "\n".join(
            [
                "結論:",
                "- ローカルモデル API に接続できず、回答を生成できませんでした。",
                "",
                "根拠:",
                f"- {_truncate_line(str(exc), 220)}",
                "",
                "参照:",
                refs,
                "",
                "不確実性:",
                *uncertainty_lines,
            ]
        )
        print(normalize_rag_blocks(out))
        return

    if ("参照:" not in out) and ("sources" not in out.lower()):
        out = out.rstrip() + "\n\n参照:\n" + "\n".join(f"- {s}" for s in sources) + "\n"

    # --- postprocess: eval S1/S2 guard ---
    # sources がある場合は、参照と不確実性を“決定論”で固定する（unknown混入を防ぐ）
    if sources:
        # sources をユニーク化（順序保持）
        _uniq = []
        for _s in sources:
            if _s and _s not in _uniq:
                _uniq.append(_s)
        sources = _uniq

        _refs_block = "\n参照:\n" + "\n".join(f"- {s}" for s in sources) + "\n"
        if "参照:" in out:
            # 正規表現ではなく文字位置探索で安全に置換
            start = out.find("\n参照:\n")
            end_match = re.search(r"\n\n不確実性:|\Z", out[start:])
            if start != -1 and end_match:
                end = start + end_match.start()
                out = out[:start] + _refs_block + out[end:]
        else:
            out = out.rstrip() + "\n\n" + _refs_block

    # 結論が空なら、根拠の先頭を結論に採用（捏造せずに穴埋め）
    _lines = out.splitlines()
    _i_conc = next((i for i, line in enumerate(_lines) if line.strip() == "結論:"), None)
    _i_evi = next((i for i, line in enumerate(_lines) if line.strip() == "根拠:"), None)
    if _i_conc is not None:
        k = _i_conc + 1
        while k < len(_lines) and _lines[k].strip() == "":
            k += 1
        if k < len(_lines) and _lines[k].lstrip().startswith("-"):
            _conc = _lines[k].lstrip()[1:].strip()
            if _conc == "" and _i_evi is not None:
                m = _i_evi + 1
                while m < len(_lines) and _lines[m].strip() == "":
                    m += 1
                if m < len(_lines) and _lines[m].lstrip().startswith("-"):
                    _ev = _lines[m].lstrip()[1:].strip()
                    if _ev:
                        _lines[k] = "- " + _ev
    out = "\n".join(_lines)

    # sources があるなら、不確実性は固定（unknown語彙を出さない）
    if sources:
        if "不確実性:" in out:
            out = re.sub(
                r"(?s)\n不確実性:\n.*$",
                "\n不確実性:\n- 不確実な情報はありません。\n",
                out,
            )
        else:
            out = out.rstrip() + "\n\n不確実性:\n- 不確実な情報はありません。\n"

    print(normalize_rag_blocks(out))


if __name__ == "__main__":
    main()
