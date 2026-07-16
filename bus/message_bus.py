from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class Topic(str, Enum):
    WORKLOAD_UPDATE = "workload.update"
    WORKLOAD_ANOMALY = "workload.anomaly"
    CANDIDATE_PROPOSED = "candidate.proposed"
    CANDIDATE_EVALUATING = "candidate.evaluating"
    TWIN_PROVISIONED = "twin.provisioned"
    TWIN_DESTROYED = "twin.destroyed"
    VALIDATION_COMPLETE = "validation.complete"
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    DEPLOYMENT_FAILED = "deployment.failed"
    ROLLBACK_TRIGGERED = "rollback.triggered"
    ROLLBACK_COMPLETED = "rollback.completed"
    POLICY_CHECK = "policy.check"
    POLICY_DECISION = "policy.decision"
    SYSTEM_HEALTH = "system.health"


@dataclass
class Message:
    topic: str
    payload: dict
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps({
            "topic": self.topic,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "timestamp": self.timestamp,
        })

    @classmethod
    def from_json(cls, data: str) -> "Message":
        d = json.loads(data)
        return cls(
            topic=d["topic"],
            payload=d["payload"],
            correlation_id=d.get("correlation_id", ""),
            source=d.get("source", ""),
            timestamp=d.get("timestamp", ""),
        )


class MessageBus:
    _instance: Optional["MessageBus"] = None

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._source = "unknown"
        self._task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> "MessageBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self, source: str = ""):
        self._source = source
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def publish(self, topic: Topic, payload: dict, correlation_id: str = ""):
        msg = Message(
            topic=topic.value,
            payload=payload,
            correlation_id=correlation_id or str(uuid4()),
            source=self._source,
        )
        await self._queue.put(msg)

    def subscribe(self, topic: Topic, handler: Callable):
        if topic.value not in self._handlers:
            self._handlers[topic.value] = []
        self._handlers[topic.value].append(handler)

    def unsubscribe(self, topic: Topic, handler: Callable):
        if topic.value in self._handlers:
            self._handlers[topic.value].remove(handler)

    async def _dispatch_loop(self):
        while self._running:
            try:
                msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                handlers = self._handlers.get(msg.topic, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(msg)
                        else:
                            handler(msg)
                    except Exception as e:
                        print(f"[bus] handler error on {msg.topic}: {e}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[bus] dispatch error: {e}")


get_bus = MessageBus.get_instance
