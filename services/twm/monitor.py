from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import psutil

from bus import MessageBus, Topic
from schemas import (
    WorkloadSignature, QueryShape, ResourceMetrics,
)


class TelemetryWorkloadMonitor:
    def __init__(
        self,
        bus: MessageBus,
        pg_dsn: str = "postgresql://postgres@localhost:5542/sedbms_prod",
        poll_interval: float = 5.0,
        anomaly_p95_threshold: float = 2.0,
    ):
        self.bus = bus
        self.pg_dsn = pg_dsn
        self.poll_interval = poll_interval
        self.anomaly_p95_threshold = anomaly_p95_threshold
        self._pg_pool: Optional[asyncpg.Pool] = None
        self._running = False
        self._baseline_p95: Dict[str, float] = {}
        self._last_signature: Optional[WorkloadSignature] = None

    async def start(self):
        self._pg_pool = await asyncpg.create_pool(self.pg_dsn, min_size=1, max_size=2)
        self._running = True
        asyncio.create_task(self._poll_loop())

    async def stop(self):
        self._running = False
        if self._pg_pool:
            await self._pg_pool.close()

    async def _poll_loop(self):
        while self._running:
            try:
                signature = await self._collect_workload_signature()
                await self._publish_if_changed(signature)
            except Exception as e:
                print(f"[twm] poll error: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _collect_workload_signature(self) -> WorkloadSignature:
        if not self._pg_pool:
            return self._empty_signature()
        async with self._pg_pool.acquire() as conn:
            query_shapes = await self._collect_query_shapes(conn)
            table_sizes = await self._collect_table_sizes(conn)
            index_usage = await self._collect_index_usage(conn)
        resource_metrics = self._collect_resource_metrics()
        return WorkloadSignature(
            query_shapes=query_shapes,
            resource_metrics=resource_metrics,
            table_sizes=table_sizes,
            index_usage=index_usage,
            hot_keys={},
            read_write_ratio=self._compute_rw_ratio(query_shapes),
            connection_count=0,
            anomaly_flags=[],
        )

    async def _collect_query_shapes(self, conn) -> List[QueryShape]:
        try:
            rows = await conn.fetch("""
                SELECT
                    regexp_replace(query, '[0-9]+', '?', 'g') AS fingerprint,
                    calls,
                    total_exec_time / NULLIF(calls, 0) AS avg_time,
                    min_exec_time,
                    max_exec_time,
                    rows,
                    shared_blks_hit + shared_blks_read AS total_blks
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat%'
                ORDER BY total_exec_time DESC
                LIMIT 50
            """)
            result = []
            for r in rows:
                fingerprint = r["fingerprint"][:200]
                tables_accessed = self._extract_tables(fingerprint)
                predicates = self._extract_predicates(fingerprint)
                result.append(QueryShape(
                    query_fingerprint=fingerprint,
                    frequency=float(r["calls"]),
                    avg_latency_ms=r["avg_time"] or 0.0,
                    p50_latency_ms=r["avg_time"] or 0.0,
                    p95_latency_ms=r["max_exec_time"] or 0.0,
                    p99_latency_ms=r["max_exec_time"] or 0.0,
                    tables_accessed=tables_accessed,
                    predicates=predicates,
                    join_count=fingerprint.upper().count(" JOIN "),
                    read_write_ratio=self._shape_rw_ratio(fingerprint),
                ))
            return result
        except Exception:
            return []

    async def _collect_table_sizes(self, conn) -> Dict[str, int]:
        try:
            rows = await conn.fetch("""
                SELECT schemaname || '.' || tablename AS name,
                       pg_total_relation_size(schemaname || '.' || tablename) AS size
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY size DESC
            """)
            return {r["name"]: r["size"] for r in rows}
        except Exception:
            return {}

    async def _collect_index_usage(self, conn) -> Dict[str, float]:
        try:
            rows = await conn.fetch("""
                SELECT i.schemaname || '.' || i.indexrelname AS name,
                       idx_scan::float / NULLIF(idx_scan + seq_scan, 0) * 100 AS usage_pct
                FROM pg_stat_user_indexes i
                JOIN pg_stat_user_tables t ON i.relid = t.relid
                ORDER BY usage_pct DESC
            """)
            return {r["name"]: r["usage_pct"] for r in rows}
        except Exception:
            return {}

    def _collect_resource_metrics(self) -> ResourceMetrics:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()
        return ResourceMetrics(
            cpu_percent=cpu,
            memory_percent=mem.percent,
            disk_read_bytes=disk.read_bytes if disk else 0,
            disk_write_bytes=disk.write_bytes if disk else 0,
            net_bytes_sent=net.bytes_sent if net else 0,
            net_bytes_recv=net.bytes_recv if net else 0,
            timestamp=datetime.now(timezone.utc),
        )

    def _compute_rw_ratio(self, shapes: List[QueryShape]) -> float:
        if not shapes:
            return 1.0
        writes = sum(1 for s in shapes if "INSERT" in s.query_fingerprint or
                     "UPDATE" in s.query_fingerprint or
                     "DELETE" in s.query_fingerprint)
        reads = len(shapes) - writes
        return reads / max(writes, 1)

    def _shape_rw_ratio(self, fingerprint: str) -> float:
        upper = fingerprint.upper()
        if upper.startswith("INSERT") or upper.startswith("UPDATE") or upper.startswith("DELETE"):
            return 0.0
        return 1.0

    def _extract_tables(self, fingerprint: str) -> List[str]:
        normalized = " ".join(fingerprint.split())
        patterns = [
            r"\bFROM\s+([a-zA-Z_][\w\.]*)",
            r"\bJOIN\s+([a-zA-Z_][\w\.]*)",
            r"\bINTO\s+([a-zA-Z_][\w\.]*)",
            r"\bUPDATE\s+([a-zA-Z_][\w\.]*)",
        ]
        tables: List[str] = []
        for pattern in patterns:
            for match in re.findall(pattern, normalized, flags=re.IGNORECASE):
                table = match if "." in match else f"public.{match}"
                if table not in tables:
                    tables.append(table)
        return tables

    def _extract_predicates(self, fingerprint: str) -> List[str]:
        normalized = " ".join(fingerprint.split())
        where_match = re.search(r"\bWHERE\s+(.+?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)", normalized, flags=re.IGNORECASE)
        if not where_match:
            return []
        clause = where_match.group(1)
        parts = re.split(r"\bAND\b|\bOR\b", clause, flags=re.IGNORECASE)
        predicates: List[str] = []
        for part in parts:
            match = re.search(r"([a-zA-Z_][\w\.]*)\s*(=|>|<|>=|<=|LIKE|IN)", part.strip(), flags=re.IGNORECASE)
            if match:
                predicates.append(match.group(1))
        return predicates

    async def _publish_if_changed(self, signature: WorkloadSignature):
        anomalies = []
        for shape in signature.query_shapes:
            fp = shape.query_fingerprint
            if fp in self._baseline_p95:
                if shape.p95_latency_ms > self._baseline_p95[fp] * self.anomaly_p95_threshold:
                    anomalies.append(f"p95_spike:{fp[:40]}")
            else:
                self._baseline_p95[fp] = shape.p95_latency_ms

        if anomalies:
            signature.anomaly_flags = anomalies
            await self.bus.publish(Topic.WORKLOAD_ANOMALY, signature.model_dump(mode="json"))

        await self.bus.publish(Topic.WORKLOAD_UPDATE, signature.model_dump(mode="json"))
        self._last_signature = signature

    def _empty_signature(self) -> WorkloadSignature:
        return WorkloadSignature(
            query_shapes=[],
            resource_metrics=self._collect_resource_metrics(),
            table_sizes={},
            index_usage={},
            hot_keys={},
            read_write_ratio=1.0,
            connection_count=0,
        )
