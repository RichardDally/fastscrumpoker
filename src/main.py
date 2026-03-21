import json
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.room import manager

app = FastAPI(title="Scrum Poker Online")

# Ensure static and templates directories exist
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/room/{room_id}", response_class=HTMLResponse)
async def room(request: Request, room_id: str):
    return templates.TemplateResponse(request, "index.html", context={"room_id": room_id})

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str, name: str = "Anonymous"):
    await manager.connect(room_id, user_id, name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            action = json.loads(data)
            await manager.process_action(room_id, user_id, action)
            
    except WebSocketDisconnect:
        await manager.disconnect(room_id, user_id)
