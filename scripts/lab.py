#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin CLI for the RomanCohort lab API v1. Standard library only."""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_BASE = os.environ.get("ROMANCOHORT_API_BASE", "https://www.romancohort.cloud/api/v1")


def die(msg, code=1):
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(code)


def get_key(args):
    key = args.key or os.environ.get("ROMANCOHORT_API_KEY", "")
    if not key:
        die("ROMANCOHORT_API_KEY is not set")
    return key


def request(args, method, path, body=None, timeout=120, stream=False):
    url = args.base.rstrip("/") + path
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + get_key(args))
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if method == "POST":
        req.add_header("Idempotency-Key", str(uuid.uuid4()))
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, resp.headers, resp
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:1000]}
        if exc.code == 401:
            payload.setdefault("hint", "set ROMANCOHORT_API_KEY")
        return exc.code, exc.headers, payload


def json_call(args, method, path, body=None, timeout=120):
    status, headers, payload = request(args, method, path, body, timeout)
    if hasattr(payload, "read"):
        raw = payload.read().decode("utf-8", "replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw": raw}
        return status, headers, data
    return status, headers, payload


def print_table(tools):
    print("%-12s %-18s %-9s %-16s %s" % ("ID", "NAME", "STATUS", "CATEGORY", "RUNTIME"))
    for t in tools:
        print("%-12s %-18s %-9s %-16s %s" % (
            t.get("id"), t.get("name"), t.get("status"), t.get("category"),
            t.get("typical_runtime", "")))
    print("\nRun `lab tools --json` for the full input schema and limits.")


def cmd_tools(args):
    status, _, data = json_call(args, "GET", "/tools")
    if status >= 400:
        die(data)
    if args.json or getattr(args, "json_sub", False):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_table(data.get("tools", []))


def cmd_health(args):
    status, _, data = json_call(args, "GET", "/health")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if status >= 400:
        raise SystemExit(1)


def load_params(args):
    if args.params_json:
        return json.loads(args.params_json)
    if not args.params:
        die("provide --params file.json or --params-json '{...}'")
    if args.params == "-":
        return json.load(sys.stdin)
    with open(args.params, encoding="utf-8") as fh:
        return json.load(fh)


def poll(args, run_id, wait=True, deadline=None):
    last = None
    while True:
        status, _, data = json_call(args, "GET", "/runs/" + run_id)
        if status >= 400:
            die(data)
        state = data.get("status")
        if state != last:
            print("[status] %s" % state, file=sys.stderr)
            last = state
        if not wait or state not in ("running", "queued"):
            return data
        if deadline and time.time() > deadline:
            die("wait timeout; run id: " + run_id)
        time.sleep(2)


def stream_logs(args, run_id, deadline):
    status, headers, payload = request(args, "GET", "/runs/" + run_id + "/events", timeout=3600)
    if status >= 400:
        print("[logs] SSE unavailable: %s" % status, file=sys.stderr)
        return
    done = False
    try:
        for raw in payload:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if not line:
                continue
            if line.startswith("event: done"):
                done = True
                continue
            if line.startswith("event: error"):
                print("[error] backend stream error", file=sys.stderr)
                done = True
                continue
            if not line.startswith("data:"):
                continue
            raw_data = line[5:].strip()
            try:
                ev = json.loads(raw_data)
                msg = ev.get("message") or ev.get("error") or raw_data
                level = ev.get("level") or ev.get("step") or "info"
                print("[%s] %s" % (level, msg))
            except Exception:
                print(raw_data)
            if time.time() > deadline:
                die("log timeout; run id: " + run_id)
    except Exception as exc:
        print("[logs] stream ended: %s; falling back to polling" % exc, file=sys.stderr)
    if done:
        return


def cmd_run(args):
    params = load_params(args)
    body = {"tool": args.tool, "params": params}
    if args.name:
        body["name"] = args.name
    status, headers, data = json_call(args, "POST", "/runs", body, timeout=90)
    if status == 409 and data.get("run_id"):
        print("[attach] %s" % data["run_id"], file=sys.stderr)
        run_id = data["run_id"]
    elif status in (200, 202) and data.get("run_id"):
        run_id = data["run_id"]
    else:
        die({"status": status, "detail": data})
    print("[run] %s" % run_id, file=sys.stderr)
    if not args.wait:
        print(json.dumps({"run_id": run_id, "status": data.get("status", "running")}, ensure_ascii=False))
        return
    stream_logs(args, run_id, time.time() + args.timeout)
    final = poll(args, run_id, True, time.time() + args.timeout)
    out = Path(args.out or "runs") / run_id
    downloaded = []
    if args.download and final.get("status") == "done":
        downloaded = download_run(args, run_id, out)
    result = {
        "run_id": run_id,
        "tool": args.tool,
        "status": final.get("status"),
        "result": final.get("result"),
        "error": final.get("error"),
        "files": final.get("files", []),
        "out": str(out) if args.download else None,
        "downloaded": downloaded
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def download_run(args, run_id, out_dir):
    status, _, manifest = json_call(args, "GET", "/runs/%s/files?hash=1" % run_id)
    if status >= 400:
        die(manifest)
    out_dir.mkdir(parents=True, exist_ok=True)
    done = []
    for item in manifest.get("files", []):
        if not item.get("downloadable"):
            print("[skip] %s (%s)" % (item.get("name"), item.get("reason", "not downloadable")),
                  file=sys.stderr)
            continue
        name = item["name"].split("/")[-1]
        dest = out_dir / name
        rel = item["url"]
        if rel.startswith("/api/v1"):
            rel = rel[len("/api/v1"):]
        status, headers, payload = request(args, "GET", rel, timeout=300)
        if status >= 400:
            print("[warn] %s: HTTP %s" % (name, status), file=sys.stderr)
            continue
        h = hashlib.sha256()
        try:
            with open(dest, "wb") as fh:
                for chunk in iter(lambda: payload.read(65536), b""):
                    fh.write(chunk)
                    h.update(chunk)
        finally:
            payload.close()
        digest = h.hexdigest()
        expected = item.get("sha256")
        ok = (not expected) or digest == expected
        done.append({"name": name, "path": str(dest), "sha256": digest, "hash_ok": ok})
        print("[file] %s -> %s%s" % (name, dest, "" if ok else " (HASH MISMATCH)"), file=sys.stderr)
    return done


def cmd_status(args):
    status, _, data = json_call(args, "GET", "/runs/" + args.run_id)
    if status >= 400:
        die(data)
    if args.json or getattr(args, "json_sub", False):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({k: data.get(k) for k in ("run_id", "tool", "status", "backend_job_id",
                                                  "created_at", "finished_at", "files")},
                         ensure_ascii=False, indent=2))


def cmd_logs(args):
    deadline = time.time() + args.timeout
    stream_logs(args, args.run_id, deadline)
    poll(args, args.run_id, True, deadline)


def cmd_files(args):
    status, _, data = json_call(args, "GET", "/runs/%s/files?hash=%d" % (args.run_id, 1 if args.hash else 0))
    if status >= 400:
        die(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_download(args):
    out = Path(args.out or "runs") / args.run_id
    print(json.dumps(download_run(args, args.run_id, out), ensure_ascii=False, indent=2))


def cmd_cancel(args):
    status, _, data = json_call(args, "POST", "/runs/" + args.run_id + "/cancel")
    if status >= 400:
        die(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_usage(args):
    status, _, data = json_call(args, "GET", "/usage")
    if status >= 400:
        die(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_samples(args):
    status, _, data = json_call(args, "GET", "/tools/%s/samples" % args.tool)
    if status >= 400:
        die(data)
    if args.json or getattr(args, "json_sub", False):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for sample in data.get("samples", []):
            print(sample)


def cmd_models(args):
    status, _, data = json_call(args, "GET", "/tools/%s/models" % args.tool)
    if status >= 400:
        die(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_datasets(args):
    status, _, data = json_call(args, "GET", "/tools/%s/datasets" % args.tool)
    if status >= 400:
        die(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_lnpdb_search(args):
    query = {
        "q": args.query,
        "cargo": args.cargo,
        "route": args.route,
        "model": args.model,
        "limit": args.limit,
        "offset": args.offset,
    }
    query = {key: value for key, value in query.items() if value not in ("", None)}
    path = "/lnpdb/search?" + urllib.parse.urlencode(query)
    status, _, data = json_call(args, "GET", path)
    if status >= 400:
        die(data)
    if args.json or getattr(args, "json_sub", False):
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    rows = data.get("rows", [])
    cols = data.get("cols", [])
    print("total=%s offset=%s limit=%s" % (
        data.get("total"), data.get("offset"), data.get("limit")))
    if cols:
        print("\t".join(cols))
    for row in rows:
        print("\t".join(str(row.get(name, "")) for name in cols))


def cmd_lnpdb_download(args):
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    status, headers, payload = request(args, "GET", "/lnpdb/download", timeout=300)
    if status >= 400:
        if hasattr(payload, "read"):
            payload.close()
        die(payload)
    expected = headers.get("Content-Length")
    digest = hashlib.sha256()
    size = 0
    tmp = dest.with_name(dest.name + ".part")
    try:
        with open(tmp, "wb") as fh:
            for chunk in iter(lambda: payload.read(65536), b""):
                fh.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    except Exception:
        payload.close()
        if tmp.exists():
            tmp.unlink()
        raise
    else:
        payload.close()
    tmp.replace(dest)
    length_ok = expected is None or int(expected) == size
    print(json.dumps({
        "path": str(dest),
        "size": size,
        "sha256": digest.hexdigest(),
        "content_length_ok": length_ok,
    }, ensure_ascii=False, indent=2))
    if not length_ok:
        die("downloaded size does not match Content-Length")


def main():
    ap = argparse.ArgumentParser(description="RomanCohort lab API client")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--key", default="")
    ap.add_argument("--json", action="store_true")
    # Python 3.6 compatibility: add_subparsers(required=True) arrived in 3.7.
    sub = ap.add_subparsers(dest="cmd")
    tp = sub.add_parser("tools")
    tp.add_argument("--json", action="store_true", dest="json_sub")
    sub.add_parser("health")
    r = sub.add_parser("run")
    r.add_argument("--tool", required=True)
    r.add_argument("--params")
    r.add_argument("--params-json")
    r.add_argument("--name")
    r.add_argument("--wait", action="store_true")
    r.add_argument("--download", action="store_true")
    r.add_argument("--out", default="runs")
    r.add_argument("--timeout", type=int, default=3600)
    s = sub.add_parser("status")
    s.add_argument("run_id")
    s.add_argument("--json", action="store_true", dest="json_sub")
    l = sub.add_parser("logs")
    l.add_argument("run_id")
    l.add_argument("--timeout", type=int, default=3600)
    f = sub.add_parser("files")
    f.add_argument("run_id")
    f.add_argument("--hash", action="store_true")
    d = sub.add_parser("download")
    d.add_argument("run_id")
    d.add_argument("--out", default="runs")
    c = sub.add_parser("cancel")
    c.add_argument("run_id")
    sm = sub.add_parser("samples")
    sm.add_argument("--tool", required=True)
    sm.add_argument("--json", action="store_true", dest="json_sub")
    mm = sub.add_parser("models")
    mm.add_argument("--tool", required=True)
    dm = sub.add_parser("datasets")
    dm.add_argument("--tool", required=True)
    ls = sub.add_parser("lnpdb-search")
    ls.add_argument("--query", default="")
    ls.add_argument("--cargo", default="")
    ls.add_argument("--route", default="")
    ls.add_argument("--model", default="")
    ls.add_argument("--limit", type=int, default=50)
    ls.add_argument("--offset", type=int, default=0)
    ls.add_argument("--json", action="store_true", dest="json_sub")
    ld = sub.add_parser("lnpdb-download")
    ld.add_argument("--out", default="LNPDB.csv")
    sub.add_parser("usage")
    args = ap.parse_args()
    if not args.cmd:
        ap.error("a command is required")
    fn = {
        "tools": cmd_tools, "health": cmd_health, "run": cmd_run,
        "status": cmd_status, "logs": cmd_logs, "files": cmd_files,
        "download": cmd_download, "cancel": cmd_cancel, "usage": cmd_usage,
        "samples": cmd_samples, "models": cmd_models, "datasets": cmd_datasets,
        "lnpdb-search": cmd_lnpdb_search, "lnpdb-download": cmd_lnpdb_download
    }[args.cmd]
    fn(args)


if __name__ == "__main__":
    main()
