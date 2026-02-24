#!/usr/bin/env python3
# stopless: no sys.exit, no argparse(SystemExit), no assert
import os, json, hashlib, sys, tempfile
from pathlib import Path

TAXONOMY_V1 = ["schema","contract","opcode","normalization","index","search","cite"]
TAXONOMY_VERSION = "TAXONOMY_v1"

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024*1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        print(f"ERROR: sha256_failed path={path} err={e}")
        return ""

def json_dump_atomic(path: str, obj) -> None:
    d = os.path.dirname(path) or "."
    tmp = ""
    try:
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tmp_json_", dir=d)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        os.replace(tmp, path)
        print(f"OK: wrote_json path={path}")
    except Exception as e:
        print(f"ERROR: write_json_failed path={path} err={e}")
        try:
            if tmp: os.unlink(tmp)
        except Exception:
            pass

def write_jsonl_atomic(path: str, rows: list) -> None:
    d = os.path.dirname(path) or "."
    tmp = ""
    try:
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tmp_jsonl_", dir=d)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            for obj in rows:
                f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        os.replace(tmp, path)
        print(f"OK: wrote_jsonl path={path} lines={len(rows)}")
    except Exception as e:
        print(f"ERROR: write_jsonl_failed path={path} err={e}")
        try:
            if tmp: os.unlink(tmp)
        except Exception:
            pass

def map_error_to_taxonomy(err: str):
    e = (err or "").strip().upper()
    # extra heuristics (S22-09): widen mapping without changing determinism
    if "DATASET_SCHEMA" in e or "JSON_SCHEMA" in e:
        return ("schema", f"error={e}")
    if "FORBIDDEN" in e or "POLICY" in e:
        return ("contract", f"error={e}")
    if "UNKNOWN_OPCODE" in e or "OPCODE_" in e:
        return ("opcode", f"error={e}")
    if "CITATION" in e or "CITE_" in e:
        return ("cite", f"error={e}")
    if "SEARCH_" in e:
        return ("search", f"error={e}")
    if "INDEX_" in e:
        return ("index", f"error={e}")

    if not e or e == "NONE":
        return ("", "")
    if "SCHEMA" in e: return ("schema", f"error={e}")
    if "CONTRACT" in e: return ("contract", f"error={e}")
    if "OPCODE" in e: return ("opcode", f"error={e}")
    if "NORMAL" in e or "NORM" in e: return ("normalization", f"error={e}")
    if "INDEX" in e: return ("index", f"error={e}")
    if "SEARCH" in e: return ("search", f"error={e}")
    if "CITE" in e or "CITATION" in e: return ("cite", f"error={e}")
    return ("contract", f"unclassified error={e}")

def parse_args(argv):
    out_dir=""; dataset=""
    i=0
    while i < len(argv):
        a=argv[i]
        if a=="--out" and i+1 < len(argv):
            out_dir=argv[i+1]; i+=2; continue
        if a=="--dataset" and i+1 < len(argv):
            dataset=argv[i+1]; i+=2; continue
        i+=1
    return out_dir, dataset

def _case_like_dict(d: dict) -> bool:
    if not isinstance(d, dict): return False
    ks=set(d.keys())
    return ("error" in ks) or ("err" in ks) or ("result_schema" in ks) or ("case_id" in ks) or ("id" in ks) or ("case" in ks)

def find_cases_in_run_json(obj):
    # returns list of dicts (case-like), possibly constructed from mapping
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and _case_like_dict(obj[0]):
            return obj
        # recurse into list items deterministically
        for it in obj:
            got = find_cases_in_run_json(it)
            if got: return got
        return []

    if isinstance(obj, dict):
        # mapping case_id -> dict ?
        if obj and all(isinstance(k,str) for k in obj.keys()) and all(isinstance(v,dict) for v in obj.values()):
            # if values look case-like, treat as map
            vs=list(obj.values())
            if vs and _case_like_dict(vs[0]):
                out=[]
                for k in sorted(obj.keys()):
                    dd=dict(obj[k])
                    dd.setdefault("case_id", k)
                    out.append(dd)
                return out

        for k in sorted(obj.keys()):
            got = find_cases_in_run_json(obj[k])
            if got: return got
    return []

def find_cases_from_cases_dir(cases_dir: Path):
    out=[]
    if not cases_dir.exists() or not cases_dir.is_dir():
        return out

    ents=sorted(cases_dir.iterdir(), key=lambda p: p.name)

    # 1) jsonl files
    for p in ents:
        if p.is_file() and p.suffix == ".jsonl":
            try:
                for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    ln=ln.strip()
                    if not ln: continue
                    try:
                        obj=json.loads(ln)
                        if isinstance(obj, dict):
                            out.append(obj)
                    except Exception:
                        pass
            except Exception:
                pass

    # 2) json files
    for p in ents:
        if p.is_file() and p.suffix == ".json":
            try:
                obj=json.load(open(p,"r",encoding="utf-8"))
                if isinstance(obj, dict):
                    obj.setdefault("case_id", p.stem)
                    out.append(obj)
            except Exception:
                pass

    # 3) subdirs with result.json/case.json
    for p in ents:
        if p.is_dir():
            for name in ["result.json","case.json","out.json","eval.json"]:
                q=p/name
                if q.exists() and q.is_file():
                    try:
                        obj=json.load(open(q,"r",encoding="utf-8"))
                        if isinstance(obj, dict):
                            obj.setdefault("case_id", p.name)
                            out.append(obj)
                        break
                    except Exception:
                        pass

    return out

def main():
    STOP="0"
    out_dir, dataset = parse_args(sys.argv[1:])
    if not out_dir:
        print("ERROR: missing --out")
        print("OK: done stop=1")
        return

    outp=Path(out_dir)
    run_json=outp/"run.json"
    summary_json=outp/"summary.json"
    cases_dir=outp/"cases"
    cases_jsonl=outp/"cases.jsonl"
    sha_sums=outp/"SHA256SUMS.txt"

    # load run.json
    run_obj={}
    if run_json.exists():
        try:
            run_obj=json.load(open(run_json,"r",encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: run_json_read_failed err={e}")
    else:
        print(f"ERROR: run_json_missing path={run_json}")

    # load summary
    summary_obj={}
    if summary_json.exists():
        try:
            summary_obj=json.load(open(summary_json,"r",encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: summary_read_failed err={e}")
            summary_obj={}
    else:
        print("SKIP: summary_missing")

    # find cases
    cases = find_cases_in_run_json(run_obj)
    if not cases:
        cases = find_cases_from_cases_dir(cases_dir)

    if not cases:
        print("ERROR: cannot_find_cases (run.json and cases/)")
        print("OK: done stop=1")
        return

    rows=[]
    counts={t:0 for t in TAXONOMY_V1}

    for c in cases:
        if not isinstance(c, dict):
            continue
        cid=str(c.get("case_id") or c.get("id") or c.get("case") or "").strip()
        err=str(c.get("error") or c.get("err") or c.get("result_schema") or "")
        tag, reason = map_error_to_taxonomy(err)
        result="OK" if (not err or err.strip().upper()=="NONE") else "ERROR"

        row={
            "case_id": cid,
            "dataset": dataset,
            "mode": "classify",
            "result": result,
            "artifacts": {
                "run_json": "run.json",
                "summary_json": "summary.json",
                "audit_json": "audit.json",
                "cases_dir": "cases",
            },
        }
        if result in ("ERROR","SKIP"):
            row["taxonomy_tag"]=tag or "contract"
            row["taxonomy_reason"]=reason or "unclassified_failure"
            counts[row["taxonomy_tag"]] = int(counts.get(row["taxonomy_tag"],0)) + 1
        rows.append(row)

    rows.sort(key=lambda r: r.get("case_id",""))
    write_jsonl_atomic(str(cases_jsonl), rows)

    sha_cases = sha256_file(str(cases_jsonl))
    summary_obj["taxonomy_version"]=TAXONOMY_VERSION
    summary_obj["counts_by_tag"]=counts
    summary_obj["sha256_cases_jsonl"]=sha_cases
    json_dump_atomic(str(summary_json), summary_obj)

    # write SHA256SUMS (sorted)
    files=["audit.json","cases.jsonl","run.json","summary.json"]
    sums=[]
    for fn in files:
        fp=outp/fn
        if fp.exists() and fp.is_file():
            sums.append((fn, sha256_file(str(fp))))
        else:
            print(f"SKIP: sha_missing file={fn}")
    sums.sort(key=lambda x:x[0])
    try:
        with open(sha_sums,"w",encoding="utf-8") as f:
            for fn, hh in sums:
                if hh:
                    f.write(f"{hh}  {fn}\n")
        print(f"OK: wrote_sha256sums path={sha_sums}")
    except Exception as e:
        print(f"ERROR: write_sha256sums_failed err={e}")

    print("OK: done stop=0")

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: crash err={e.__class__.__name__}")
        print("OK: done stop=1")
