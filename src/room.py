import logging
from fastapi import WebSocket
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Participant(BaseModel):
    user_id: str
    name: str
    vote: str | None = None
    connected: bool = True
    is_host: bool = False

class RoomState(BaseModel):
    room_id: str
    participants: dict[str, Participant] = {}
    revealed: bool = False

class RoomManager:
    def __init__(self):
        # Maps room_id to RoomState
        self.rooms: dict[str, RoomState] = {}
        # Maps user_id to WebSocket connection
        self.active_connections: dict[str, WebSocket] = {}

    def get_or_create_room(self, room_id: str) -> RoomState:
        if room_id not in self.rooms:
            self.rooms[room_id] = RoomState(room_id=room_id)
        return self.rooms[room_id]

    async def connect(self, room_id: str, user_id: str, name: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        room = self.get_or_create_room(room_id)
        
        # Check if they are the first participant, making them host
        is_host = len(room.participants) == 0
        
        if user_id in room.participants:
            room.participants[user_id].connected = True
            room.participants[user_id].name = name
            logger.info(f"User {name} ({user_id}) reconnected to room {room_id}. Host: {room.participants[user_id].is_host}")
        else:
            room.participants[user_id] = Participant(
                user_id=user_id, name=name, is_host=is_host
            )
            logger.info(f"User {name} ({user_id}) joined room {room_id}. Host: {is_host}")
            
        await self.broadcast_room_state(room_id)

    async def disconnect(self, room_id: str, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        if room_id in self.rooms:
            room = self.rooms[room_id]
            if user_id in room.participants:
                p_name = room.participants[user_id].name
                room.participants[user_id].connected = False
                logger.info(f"User {p_name} ({user_id}) disconnected from room {room_id}")
                # If host leaves permanently we could re-assign host, but we just mark disconnected for now
            # Only broadcast if room still has active users, otherwise cleanup?
            # Let's keep the room forever for simplicity, but we will broadcast the status
            await self.broadcast_room_state(room_id)

    async def process_action(self, room_id: str, user_id: str, action: dict):
        room = self.get_or_create_room(room_id)
        participant = room.participants.get(user_id)
        if not participant:
            return

        action_type = action.get("action")
        p_name = participant.name
        logger.info(f"Processing action '{action_type}' for room {room_id} from user {p_name} ({user_id})")
        
        if action_type == "vote":
            # Can only vote if not revealed
            if not room.revealed:
                vote_value = action.get("value")
                participant.vote = str(vote_value)
                logger.info(f"User {p_name} ({user_id}) in room {room_id} voted: {vote_value}")
        
        elif action_type == "reveal" and participant.is_host:
            room.revealed = True
            logger.info(f"Host {p_name} ({user_id}) revealed votes in room {room_id}")
            
        elif action_type == "reset" and participant.is_host:
            room.revealed = False
            for p in room.participants.values():
                p.vote = None
            logger.info(f"Host {p_name} ({user_id}) reset room {room_id}")
                
        elif action_type == "kick" and participant.is_host:
            target_id = action.get("target_id")
            if target_id and target_id in room.participants:
                target_name = room.participants[target_id].name
                del room.participants[target_id]
                logger.info(f"Host {p_name} ({user_id}) kicked user {target_name} ({target_id}) from room {room_id}")
                # Also close their websocket if active
                if target_id in self.active_connections:
                    ws = self.active_connections[target_id]
                    await ws.close()
                    del self.active_connections[target_id]

        await self.broadcast_room_state(room_id)

    def get_room_state_for_client(self, room: RoomState, for_user_id: str) -> dict:
        """Hide votes if not revealed (except for the user's own vote)"""
        participants_data = []
        for p in room.participants.values():
            if not p.connected and p.vote is None:
                # Optionally filter out disconnected users who Haven't voted 
                pass
                
            vote = p.vote
            if not room.revealed and p.user_id != for_user_id and vote is not None:
                vote = "hidden" # Indicate they have voted, but hide the value
                
            participants_data.append({
                "user_id": p.user_id,
                "name": p.name,
                "vote": vote,
                "connected": p.connected,
                "is_host": p.is_host,
                "has_voted": p.vote is not None
            })
            
        # sort participants by name or host status for consistent UI
        participants_data.sort(key=lambda x: (not x["is_host"], x["name"].lower()))
            
        return {
            "room_id": room.room_id,
            "revealed": room.revealed,
            "participants": participants_data,
            "my_user_id": for_user_id
        }

    async def broadcast_room_state(self, room_id: str):
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        
        # We need to send custom state to each user due to vote hiding
        for user_id, p in room.participants.items():
            if p.connected and user_id in self.active_connections:
                ws = self.active_connections[user_id]
                state = self.get_room_state_for_client(room, user_id)
                try:
                    await ws.send_json({"type": "state_update", "state": state})
                except Exception:
                    # Connection might be closed midway
                    pass

manager = RoomManager()
