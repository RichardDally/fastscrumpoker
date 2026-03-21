import asyncio

import pytest

from src.room import RoomManager


class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.messages.append(data)

    async def close(self):
        self.closed = True

@pytest.fixture
def manager():
    return RoomManager()

@pytest.mark.asyncio
async def test_get_or_create_room(manager):
    room = manager.get_or_create_room("room1")
    assert getattr(room, "room_id", getattr(room, "id", "room1")) == "room1"  # Pydantic safety
    assert "room1" in manager.rooms
    
    room2 = manager.get_or_create_room("room1")
    assert room is room2

@pytest.mark.asyncio
async def test_connect(manager):
    ws = MockWebSocket()
    await manager.connect("room1", "user1", "Alice", ws)
    
    assert ws.accepted
    assert "user1" in manager.active_connections
    room = manager.rooms["room1"]
    assert len(room.participants) == 1
    assert room.participants["user1"].name == "Alice"
    assert room.participants["user1"].is_host is True
    
    # Broadcast should have sent state update
    assert len(ws.messages) == 1
    state = ws.messages[0]["state"]
    assert state["participants"][0]["name"] == "Alice"

@pytest.mark.asyncio
async def test_connect_existing_user(manager):
    ws = MockWebSocket()
    await manager.connect("room1", "user1", "Alice", ws)
    
    # Simulate disconnect and reconnect with same user_id, new name
    await manager.disconnect("room1", "user1")
    # Disconnect spawns broadcast task, let it run
    await asyncio.sleep(0)
    
    ws2 = MockWebSocket()
    await manager.connect("room1", "user1", "Alice Updated", ws2)
    
    room = manager.rooms["room1"]
    assert room.participants["user1"].name == "Alice Updated"
    assert room.participants["user1"].connected is True

@pytest.mark.asyncio
async def test_disconnect(manager):
    ws = MockWebSocket()
    await manager.connect("room1", "user1", "Alice", ws)
    await manager.disconnect("room1", "user1")
    
    assert "user1" not in manager.active_connections
    room = manager.rooms["room1"]
    assert room.participants["user1"].connected is False
    # Disconnect spawns broadcast task...

@pytest.mark.asyncio
async def test_process_action_vote(manager):
    ws1 = MockWebSocket()
    await manager.connect("room1", "u1", "Alice", ws1)
    
    await manager.process_action("room1", "u1", {"action": "vote", "value": "5"})
    room = manager.rooms["room1"]
    assert room.participants["u1"].vote == "5"

@pytest.mark.asyncio
async def test_process_action_reveal_and_reset(manager):
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    await manager.connect("room_reveal", "u1", "Host", ws1)
    await manager.connect("room_reveal", "u2", "Guest", ws2)
    
    # Vote first
    await manager.process_action("room_reveal", "u2", {"action": "vote", "value": "8"})
    
    room = manager.rooms["room_reveal"]
    assert not room.revealed
    
    # Guest tries to reveal (should be ignored, not host)
    await manager.process_action("room_reveal", "u2", {"action": "reveal"})
    assert not room.revealed
    
    # Host reveals
    await manager.process_action("room_reveal", "u1", {"action": "reveal"})
    assert room.revealed
    
    # Try voting after reveal (should be ignored)
    await manager.process_action("room_reveal", "u1", {"action": "vote", "value": "13"})
    assert room.participants["u1"].vote is None
    
    # Reset
    await manager.process_action("room_reveal", "u1", {"action": "reset"})
    assert not room.revealed
    assert room.participants["u2"].vote is None

@pytest.mark.asyncio
async def test_process_action_kick(manager):
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    await manager.connect("room_kick", "u1", "Host", ws1)
    await manager.connect("room_kick", "u2", "Guest", ws2)
    
    # Guest tries to kick Host (ignored)
    await manager.process_action("room_kick", "u2", {"action": "kick", "target_id": "u1"})
    room = manager.rooms["room_kick"]
    assert "u1" in room.participants
    
    # Host kicks Guest
    await manager.process_action("room_kick", "u1", {"action": "kick", "target_id": "u2"})
    assert "u2" not in room.participants
    assert ws2.closed is True
    assert "u2" not in manager.active_connections
