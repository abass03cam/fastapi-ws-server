from typing import Dict, List, Tuple
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Projektbasis
BASE_DIR = Path(__file__).resolve().parent

# /static → Ordner "static"
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# rooms["roomname"] = [(websocket, username), ...]
rooms: Dict[str, List[Tuple[WebSocket, str]]] = {}


# ------------------------------------------------------------
# HTTP-Routen für deine Seiten
# ------------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/client")
async def chat_client():
    return FileResponse(BASE_DIR / "templates" / "chat.html")


@app.get("/three")
async def three_client():
    return FileResponse(BASE_DIR / "templates" / "three.html")


# ------------------------------------------------------------
# WebSocket: Chat + Objektbewegung (Three.js)
# ------------------------------------------------------------

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    # Verbindung annehmen
    await websocket.accept()

    room = (room or "lobby").strip()
    username = (username or "Anon").strip()

    # Room-Liste vorbereiten
    if room not in rooms:
        rooms[room] = []

    # Diesen Client merken
    rooms[room].append((websocket, username))

    try:
        while True:
            # Nachricht vom Client empfangen (Text)
            raw = await websocket.receive_text()

            # JSON versuchen, sonst als Chat-Text behandeln
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "chat", "text": raw}

            msg_type = data.get("type", "chat")

            # 3D-Bewegung (Three.js)
            if msg_type == "object_move":
                msg = {
                    "type": "object_move",
                    "user": username,
                    "id": data.get("id", "cube-1"),
                    "position": data.get("position", {}),
                    "rotation": data.get("rotation", {}),
                }

            # Chat-Nachricht
            elif msg_type == "chat":
                msg = {
                    "type": "chat",
                    "user": username,
                    "text": data.get("text", ""),
                }

            # Andere Typen (falls du mal erweiterst)
            else:
                msg = {
                    "type": msg_type,
                    "user": username,
                    "text": data.get("text", ""),
                }

            # 👉 Broadcast an alle im gleichen Room
            for websocket_client, client_name in rooms[room]:
                await websocket_client.send_json(msg)

    finally:
        # Aufräumen bei Disconnect
        if room in rooms and (websocket, username) in rooms[room]:
            rooms[room].remove((websocket, username))
            if not rooms[room]:
                del rooms[room]
# ------------------------------------------------------------
