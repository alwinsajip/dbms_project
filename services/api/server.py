from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.cvs import ConfigVersionStore
from bus import MessageBus, Topic


class StatusResponse(BaseModel):
    service: str
    status: str
    uptime: float
    version: str = "0.1.0"


class CandidateSummary(BaseModel):
    id: str
    title: str
    domain: str
    status: str
    timestamp: str
    predicted_improvement: Optional[float] = None


def _rows_as_dicts(cursor) -> List[dict]:
    return [dict(row) for row in cursor.fetchall()]


def create_app(cvs: ConfigVersionStore, bus: Optional[MessageBus] = None):
    app = FastAPI(title="SEDBMS Control API", version="0.1.0")
    start_time = datetime.now(timezone.utc)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/status", response_model=StatusResponse)
    async def get_status():
        uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
        return StatusResponse(service="sedbms-api", status="running", uptime=uptime)

    @app.get("/api/candidates")
    async def list_candidates(domain: Optional[str] = None, status: Optional[str] = None):
        cur = cvs._conn.cursor()
        where_clauses = []
        params = []
        if domain:
            where_clauses.append("domain = ?")
            params.append(domain)
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        cur.execute(f"SELECT id, title, domain, status, timestamp, predicted_improvement FROM candidates {where} ORDER BY timestamp DESC LIMIT 100", params)
        rows = _rows_as_dicts(cur)
        return [
            CandidateSummary(
                id=row["id"],
                title=row["title"],
                domain=row["domain"],
                status=row["status"],
                timestamp=row["timestamp"],
                predicted_improvement=row["predicted_improvement"],
            )
            for row in rows
        ]

    @app.get("/api/candidates/{candidate_id}")
    async def get_candidate(candidate_id: str):
        c = cvs.get_candidate(candidate_id)
        if not c:
            raise HTTPException(404, "Candidate not found")
        report = cvs.get_validation_report(candidate_id)
        deployments = cvs.get_deployment_events(candidate_id)
        return {"candidate": c, "validation_report": report, "deployments": deployments}

    @app.get("/api/deployments")
    async def list_deployments():
        cur = cvs._conn.cursor()
        cur.execute("SELECT * FROM deployment_events ORDER BY timestamp DESC LIMIT 50")
        return _rows_as_dicts(cur)

    @app.get("/api/rollbacks")
    async def list_rollbacks():
        cur = cvs._conn.cursor()
        cur.execute("SELECT * FROM rollback_events ORDER BY timestamp DESC LIMIT 50")
        return _rows_as_dicts(cur)

    @app.get("/api/telemetry")
    async def get_telemetry():
        cur = cvs._conn.cursor()
        cur.execute("SELECT * FROM config_snapshots ORDER BY timestamp DESC LIMIT 1")
        snap = cur.fetchone()
        return {"latest_snapshot": dict(snap) if snap else None}

    if bus:
        @app.post("/api/trigger/evaluate")
        async def trigger_evaluation(candidate_id: str):
            c = cvs.get_candidate(candidate_id)
            if not c:
                raise HTTPException(404, "Candidate not found")
            import asyncio
            asyncio.create_task(bus.publish(Topic.CANDIDATE_PROPOSED, c, c.get("correlation_id", "")))
            return {"status": "evaluation_triggered", "candidate_id": candidate_id}

    return app
