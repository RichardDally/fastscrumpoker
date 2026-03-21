import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.room import manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_manager():
    # Reset room state before each test
    manager.rooms = {}
    manager.active_connections = {}

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "Scrum Poker" in response.text

def test_room_page():
    response = client.get("/room/test_room_123")
    assert response.status_code == 200
    assert "test_room_123" in response.text

def test_websocket_flow():
    with client.websocket_connect("/ws/test_room/user1?name=Alice") as ws1:
        # Initial connect should send state
        data = ws1.receive_json()
        assert data["type"] == "state_update"
        state = data["state"]
        part = state["participants"][0]
        assert part["name"] == "Alice"
        assert part["is_host"] is True

        # Alice votes
        ws1.send_json({"action": "vote", "value": "5"})
        data = ws1.receive_json()
        assert data["state"]["participants"][0]["has_voted"] is True

        # Join second user
        with client.websocket_connect("/ws/test_room/user2?name=Bob") as ws2:
            data_bob = ws2.receive_json()
            # Alice also receives update that Bob joined
            data_alice = ws1.receive_json()

            assert len(data_bob["state"]["participants"]) == 2
            
            # Bob should not see Alice's vote value since it's not revealed
            alice_state_for_bob = next(p for p in data_bob["state"]["participants"] if p["name"] == "Alice")
            assert alice_state_for_bob["has_voted"] is True
            assert alice_state_for_bob["vote"] == "hidden"
            
            # Alice reveals
            ws1.send_json({"action": "reveal"})
            
            # Both get the update
            data_alice = ws1.receive_json()
            data_bob = ws2.receive_json()
            
            assert data_alice["state"]["revealed"] is True
            assert data_bob["state"]["revealed"] is True
            
            # Bob should now see Alice's vote value
            alice_state_for_bob = next(p for p in data_bob["state"]["participants"] if p["name"] == "Alice")
            assert alice_state_for_bob["vote"] == "5"

            # Alice resets
            ws1.send_json({"action": "reset"})
            
            data_alice = ws1.receive_json()
            data_bob = ws2.receive_json()
            
            assert data_alice["state"]["revealed"] is False
            assert data_bob["state"]["revealed"] is False
            
            # Bob should see Alice's vote empty again
            alice_state_for_bob = next(p for p in data_bob["state"]["participants"] if p["name"] == "Alice")
            assert alice_state_for_bob["has_voted"] is False
