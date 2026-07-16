from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = Path(sys.executable)
API_BASE = "http://127.0.0.1:8080/api"


def wait_for_api(timeout_seconds: float = 30.0) -> dict:
    deadline = time.time() + timeout_seconds
    last_error = "API did not respond"
    while time.time() < deadline:
        try:
            response = httpx.get(f"{API_BASE}/status", timeout=2.0)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # pragma: no cover - exercised live
            last_error = str(exc)
            time.sleep(1.0)
    raise RuntimeError(last_error)


def run() -> int:
    runtime_log = REPO_ROOT / "runtime.log"
    report_path = REPO_ROOT / "live_validation_report.json"
    cvs_path = REPO_ROOT / "live_validation.sqlite"
    if runtime_log.exists():
        runtime_log.unlink()
    if cvs_path.exists():
        cvs_path.unlink()

    env = os.environ.copy()
    env["SEDBMS_CVS_PATH"] = str(cvs_path)
    main_proc = subprocess.Popen(
        [str(PYTHON), "main.py"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        status = wait_for_api()

        workload = subprocess.run(
            [
                str(PYTHON),
                "scripts/generate_workload.py",
                "--duration",
                "0.4",
                "--drift-after",
                "0.1",
                "--opm",
                "240",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=90,
            check=True,
        )

        time.sleep(10)

        conn = sqlite3.connect(str(cvs_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT domain, status, title FROM candidates ORDER BY timestamp DESC")
        candidates = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM validation_reports ORDER BY timestamp DESC")
        validations = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM deployment_events ORDER BY timestamp DESC")
        deployments = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM rollback_events ORDER BY timestamp DESC")
        rollbacks = [dict(r) for r in cur.fetchall()]
        conn.close()

        report = {
            "status": status,
            "candidate_count": len(candidates),
            "validation_count": len(validations),
            "deployment_count": len(deployments),
            "rollback_count": len(rollbacks),
            "sample_candidate_titles": [c.get("title") for c in candidates[:8]],
            "candidate_domains": sorted({c.get("domain") for c in candidates}),
            "workload_stdout_tail": workload.stdout.splitlines()[-20:],
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    finally:
        main_proc.terminate()
        try:
            main_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            main_proc.kill()
            main_proc.wait(timeout=5)

        output = ""
        if main_proc.stdout:
            output = main_proc.stdout.read()
        if output:
            runtime_log.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(run())
