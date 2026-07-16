from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ConfigVersionStore:
    def __init__(self, db_path: str = "sedbms_cvs.sqlite"):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        if self._conn:
            self._conn.close()

    def _init_schema(self):
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS config_snapshots (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                correlation_id TEXT,
                schema_ddl TEXT DEFAULT '{}',
                index_definitions TEXT DEFAULT '{}',
                partition_map TEXT DEFAULT '{}',
                compression_settings TEXT DEFAULT '{}',
                execution_config TEXT DEFAULT '{}',
                workload_signature_id TEXT
            );
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                correlation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                domain TEXT NOT NULL,
                title TEXT,
                description TEXT,
                ddl_statements TEXT DEFAULT '[]',
                config_deltas TEXT DEFAULT '[]',
                predicted_improvement REAL,
                predicted_risk REAL,
                confidence_score REAL,
                status TEXT DEFAULT 'proposed',
                rejection_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS validation_reports (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                passed INTEGER NOT NULL,
                correctness_results TEXT DEFAULT '[]',
                performance_results TEXT DEFAULT '[]',
                twin_id TEXT,
                duration_seconds REAL DEFAULT 0.0,
                details TEXT
            );
            CREATE TABLE IF NOT EXISTS deployment_events (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                strategy TEXT NOT NULL,
                status TEXT NOT NULL,
                health_check_passed INTEGER,
                pre_deploy_snapshot_id TEXT,
                post_deploy_snapshot_id TEXT,
                duration_seconds REAL,
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS rollback_events (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                trigger_reason TEXT NOT NULL,
                pre_rollback_metrics TEXT,
                post_rollback_metrics TEXT,
                duration_seconds REAL,
                success INTEGER DEFAULT 1,
                diagnostic_bundle TEXT
            );
        """)
        self._conn.commit()

    def save_snapshot(self, snapshot: dict) -> str:
        sid = snapshot.get("id", str(uuid4()))
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO config_snapshots
                (id, timestamp, correlation_id, schema_ddl, index_definitions,
                 partition_map, compression_settings, execution_config, workload_signature_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sid, snapshot.get("timestamp", datetime.now(timezone.utc).isoformat()),
            snapshot.get("correlation_id"),
            json.dumps(snapshot.get("schema_ddl", {})),
            json.dumps(snapshot.get("index_definitions", {})),
            json.dumps(snapshot.get("partition_map", {})),
            json.dumps(snapshot.get("compression_settings", {})),
            json.dumps(snapshot.get("execution_config", {})),
            snapshot.get("workload_signature_id"),
        ))
        self._conn.commit()
        return sid

    def save_candidate(self, candidate: dict) -> str:
        cid = candidate.get("id", str(uuid4()))
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO candidates
                (id, correlation_id, timestamp, domain, title, description,
                 ddl_statements, config_deltas, predicted_improvement,
                 predicted_risk, confidence_score, status, rejection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cid, candidate["correlation_id"], candidate.get("timestamp", datetime.now(timezone.utc).isoformat()),
            candidate["domain"], candidate.get("title"), candidate.get("description"),
            json.dumps(candidate.get("ddl_statements", [])),
            json.dumps(candidate.get("config_deltas", [])),
            candidate.get("predicted_improvement"), candidate.get("predicted_risk"),
            candidate.get("confidence_score"), candidate.get("status", "proposed"),
            candidate.get("rejection_reason"),
        ))
        self._conn.commit()
        return cid

    def save_validation_report(self, report: dict) -> str:
        rid = report.get("id", str(uuid4()))
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO validation_reports
                (id, candidate_id, correlation_id, timestamp, passed,
                 correctness_results, performance_results, twin_id,
                 duration_seconds, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rid, report["candidate_id"], report["correlation_id"],
            report.get("timestamp", datetime.now(timezone.utc).isoformat()),
            1 if report.get("passed") else 0,
            json.dumps(report.get("correctness_results", [])),
            json.dumps(report.get("performance_results", [])),
            report.get("twin_id"), report.get("duration_seconds", 0.0),
            report.get("details"),
        ))
        self._conn.commit()
        return rid

    def save_deployment_event(self, event: dict) -> str:
        eid = event.get("id", str(uuid4()))
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO deployment_events
                (id, candidate_id, correlation_id, timestamp, strategy, status,
                 health_check_passed, pre_deploy_snapshot_id, post_deploy_snapshot_id,
                 duration_seconds, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eid, event["candidate_id"], event["correlation_id"],
            event.get("timestamp", datetime.now(timezone.utc).isoformat()),
            event["strategy"], event["status"], event.get("health_check_passed"),
            event.get("pre_deploy_snapshot_id"), event.get("post_deploy_snapshot_id"),
            event.get("duration_seconds"), event.get("error"),
        ))
        self._conn.commit()
        return eid

    def save_rollback_event(self, event: dict) -> str:
        eid = event.get("id", str(uuid4()))
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO rollback_events
                (id, candidate_id, correlation_id, timestamp, trigger_reason,
                 pre_rollback_metrics, post_rollback_metrics, duration_seconds,
                 success, diagnostic_bundle)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eid, event["candidate_id"], event["correlation_id"],
            event.get("timestamp", datetime.now(timezone.utc).isoformat()),
            event["trigger_reason"],
            json.dumps(event.get("pre_rollback_metrics", {})),
            json.dumps(event.get("post_rollback_metrics", {})),
            event.get("duration_seconds"),
            1 if event.get("success", True) else 0,
            json.dumps(event.get("diagnostic_bundle", {})),
        ))
        self._conn.commit()
        return eid

    def get_latest_snapshot(self) -> Optional[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM config_snapshots ORDER BY timestamp DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            d = dict(row)
            for key in ("schema_ddl", "index_definitions", "partition_map", "compression_settings", "execution_config"):
                d[key] = json.loads(d[key])
            return d
        return None

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["ddl_statements"] = json.loads(d["ddl_statements"])
            d["config_deltas"] = json.loads(d["config_deltas"])
            return d
        return None

    def get_deployment_events(self, candidate_id: str) -> List[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM deployment_events WHERE candidate_id = ? ORDER BY timestamp", (candidate_id,))
        return [dict(r) for r in cur.fetchall()]

    def get_validation_report(self, candidate_id: str) -> Optional[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM validation_reports WHERE candidate_id = ? ORDER BY timestamp DESC LIMIT 1", (candidate_id,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["correctness_results"] = json.loads(d["correctness_results"])
            d["performance_results"] = json.loads(d["performance_results"])
            d["passed"] = bool(d["passed"])
            return d
        return None

    def get_rejected_candidate_ids(self) -> List[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM candidates WHERE status IN ('failed', 'rejected')")
        return [r["id"] for r in cur.fetchall()]
