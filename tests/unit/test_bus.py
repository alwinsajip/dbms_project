import pytest
from bus import MessageBus, Topic, Message


@pytest.mark.asyncio
async def test_message_serialization():
    msg = Message(topic="test.topic", payload={"key": "value"}, source="test")
    data = msg.to_json()
    decoded = Message.from_json(data)
    assert decoded.topic == "test.topic"
    assert decoded.payload["key"] == "value"
    assert decoded.source == "test"


@pytest.mark.asyncio
async def test_bus_publish_subscribe():
    bus = MessageBus()
    await bus.start("test")
    received = []

    async def handler(msg):
        received.append(msg)

    bus.subscribe(Topic.SYSTEM_HEALTH, handler)
    await bus.publish(Topic.SYSTEM_HEALTH, {"status": "ok"}, "corr-1")
    await bus.publish(Topic.SYSTEM_HEALTH, {"status": "ok2"}, "corr-2")
    import asyncio
    await asyncio.sleep(0.1)
    await bus.stop()
    assert len(received) == 2
    assert received[0].payload["status"] == "ok"
