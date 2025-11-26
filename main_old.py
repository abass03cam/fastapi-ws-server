from datetime import datetime
from typing import Dict, List, Tuple
import json

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

# rooms[room_name] = List[(WebSocket, username)]
rooms: Dict[str, List[Tuple[WebSocket, str]]] = {}


def now_ts() -> str:
    """ISO-Zeitstempel in UTC (z.B. 2025-11-26T00:00:00Z)."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ======================================================================
# 1) Startseite
# ======================================================================
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>FastAPI WebSockets — Demo</title>
      <style>
        body {
          font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
          background: linear-gradient(135deg, #0f172a, #111827);
          color: #e5e7eb;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          margin: 0;
        }
        .card {
          background: rgba(15,23,42,0.95);
          border-radius: 16px;
          padding: 24px 28px;
          box-shadow: 0 18px 45px rgba(0,0,0,0.45);
          max-width: 480px;
          width: 100%;
          border: 1px solid rgba(148,163,184,0.3);
        }
        h1 { margin-top: 0; font-size: 1.4rem; }
        p { margin: 6px 0 14px; color: #9ca3af; }
        a {
          display: inline-block;
          margin-top: 6px;
          padding: 9px 16px;
          border-radius: 999px;
          background: #4f46e5;
          color: white;
          text-decoration: none;
          font-size: 0.95rem;
        }
        a:hover { background:#6366f1; }
        code { background: rgba(15,23,42,0.9); padding: 2px 4px; border-radius: 4px; }
      </style>
    </head>
    <body>
      <div class="card">
        <h1>FastAPI WebSockets — Rooms + 3D</h1>
        <p>Kleine Demo mit:</p>
        <ul>
          <li>JSON-Chat mit Rooms</li>
          <li>Three.js Objekt, das synchron bewegt wird</li>
        </ul>
        <p>
          👉 <a href="/client">Text-Chat (Rooms)</a><br>
          👉 <a href="/three">Three.js Sync-Objekt</a>
        </p>
        <p style="font-size:0.8rem; color:#6b7280;">
          WebSocket-Endpunkt: <code>/ws/&lt;room&gt;/&lt;username&gt;</code>
        </p>
      </div>
    </body>
    </html>
    """


# ======================================================================
# 2) Einfacher JSON-Chat-Client mit Rooms (wie bisher, leicht kompakt)
# ======================================================================
html_client = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>WS JSON Chat — Rooms</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      background: #020617;
      color: #e5e7eb;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 16px;
    }
    .shell {
      background: #020617;
      border-radius: 18px;
      border: 1px solid rgba(148,163,184,0.2);
      box-shadow: 0 18px 40px rgba(15,23,42,0.8);
      max-width: 720px;
      width: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(0, 2fr);
      overflow: hidden;
    }
    @media (max-width: 720px) {
      .shell { grid-template-columns: 1fr; }
    }
    .left {
      padding: 18px 18px 16px;
      border-right: 1px solid rgba(31,41,55,0.9);
      background: radial-gradient(circle at top left, #1d2540 0, #020617 55%);
    }
    .right { padding: 16px; background: #020617; }
    h1 { margin: 0 0 6px; font-size: 1.1rem; }
    .hint { font-size: 0.85rem; color: #9ca3af; margin-bottom: 12px; }
    label {
      font-size: 0.8rem; color: #9ca3af;
      display: block; margin-top: 8px; margin-bottom: 4px;
    }
    input {
      width: 100%; padding: 7px 10px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.6);
      background: rgba(15,23,42,0.9);
      color: #e5e7eb;
      font-size: 0.85rem; outline: none;
    }
    input:focus {
      border-color: #6366f1;
      box-shadow: 0 0 0 1px rgba(99,102,241,0.5);
    }
    button {
      border: none; border-radius: 999px;
      padding: 7px 14px; font-size: 0.85rem;
      cursor: pointer; background: #4f46e5; color: #e5e7eb;
      white-space: nowrap;
    }
    button:hover { background: #6366f1; }
    button:disabled { opacity: 0.6; cursor: default; }
    .pill {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 4px 10px; font-size: 0.75rem;
      border-radius: 999px;
      background: rgba(15,23,42,0.9);
      border: 1px solid rgba(148,163,184,0.4);
      margin-top: 8px;
    }
    .badge-dot {
      width: 6px; height: 6px; border-radius: 50%; background: #22c55e;
    }
    .who { margin-top: 10px; font-size: 0.85rem; }
    .who span { font-weight: 600; color: #e5e7eb; }
    .room-name { font-weight: 600; color: #a5b4fc; }
    .msg-row { display: flex; gap: 8px; margin-top: 10px; }
    .msg-row input { flex: 1; border-radius: 999px; }
    #log {
      list-style: none; padding: 0; margin: 0;
      max-height: 260px; overflow-y: auto;
      font-size: 0.85rem;
    }
    #log li {
      padding: 4px 0;
      border-bottom: 1px solid rgba(30,41,59,0.7);
    }
    #log li:last-child { border-bottom: none; }
    .ts { color: #6b7280; font-size: 0.75rem; margin-right: 6px; }
    .user { font-weight: 600; margin-right: 4px; }
    .system { color: #9ca3af; font-style: italic; }
    .join { color: #22c55e; }
    .leave { color: #f97373; }
  </style>
</head>
<body>
  <div class="shell">
    <div class="left">
      <h1>WS JSON Chat — Rooms</h1>
      <p class="hint">
        Nutze einen <strong>Room</strong> wie <code>lobby</code>, <code>dev</code>, <code>test</code>…
      </p>

      <label for="roomInput">Room</label>
      <input id="roomInput" type="text" value="lobby" />

      <label for="nameInput">Dein Name</label>
      <input id="nameInput" type="text" value="Abass" />

      <div style="margin-top: 10px;">
        <button id="connectBtn" onclick="connect()">Verbinden</button>
      </div>

      <div class="pill" style="margin-top: 16px;" id="statusPill">
        <span class="badge-dot" id="statusDot" style="background:#f97316;"></span>
        <span id="statusText">Getrennt</span>
      </div>

      <div class="who" id="whoBox" style="display:none;">
        Verbunden als <span id="whoName"></span> in
        <span class="room-name" id="whoRoom"></span>
      </div>

      <div class="msg-row">
        <input id="msgInput" type="text" placeholder="Nachricht..." disabled />
        <button id="sendBtn" onclick="sendMsg()" disabled>Senden</button>
      </div>
    </div>

    <div class="right">
      <h2 style="margin:0 0 8px;font-size:0.95rem;">Log</h2>
      <ul id="log"></ul>
    </div>
  </div>

  <script>
    let ws = null;

    function setStatus(connected, name = "", room = "") {
      const dot = document.getElementById("statusDot");
      const txt = document.getElementById("statusText");
      const msgInput = document.getElementById("msgInput");
      const sendBtn = document.getElementById("sendBtn");
      const whoBox = document.getElementById("whoBox");
      const whoName = document.getElementById("whoName");
      const whoRoom = document.getElementById("whoRoom");

      if (connected) {
        dot.style.background = "#22c55e";
        txt.textContent = "Verbunden";
        msgInput.disabled = false;
        sendBtn.disabled = false;
        whoBox.style.display = "block";
        whoName.textContent = name;
        whoRoom.textContent = room;
      } else {
        dot.style.background = "#f97316";
        txt.textContent = "Getrennt";
        msgInput.disabled = true;
        sendBtn.disabled = true;
        whoBox.style.display = "none";
      }
    }

    function appendLog(data) {
      const log = document.getElementById("log");
      const li = document.createElement("li");

      const spanTs = document.createElement("span");
      spanTs.className = "ts";
      spanTs.textContent = "[" + data.ts + "]";

      const spanUser = document.createElement("span");
      spanUser.className = "user";
      spanUser.textContent = data.user + ":";

      const spanText = document.createElement("span");
      spanText.textContent = " " + data.text;

      li.appendChild(spanTs);
      li.appendChild(spanUser);
      li.appendChild(spanText);

      if (data.type === "join") {
        li.classList.add("system", "join");
      } else if (data.type === "leave") {
        li.classList.add("system", "leave");
      }

      log.appendChild(li);
      log.scrollTop = log.scrollHeight;
    }

    function connect() {
      if (ws && ws.readyState === WebSocket.OPEN) return;

      const room = document.getElementById("roomInput").value.trim() || "lobby";
      const name = document.getElementById("nameInput").value.trim() || "Anon";

      const url = "ws://" + location.host + "/ws/" +
                  encodeURIComponent(room) + "/" +
                  encodeURIComponent(name);

      ws = new WebSocket(url);

      ws.onopen = () => setStatus(true, name, room);

      ws.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch (e) {
          console.error("JSON parse error:", event.data);
          return;
        }
        appendLog(data);
      };

      ws.onclose = () => setStatus(false);
      ws.onerror = () => setStatus(false);
    }

    function sendMsg() {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const input = document.getElementById("msgInput");
      const text = input.value.trim();
      if (!text) return;

      // Wir schicken hier JSON (type=chat)
      const payload = {
        type: "chat",
        text: text
      };
      ws.send(JSON.stringify(payload));
      input.value = "";
    }

    document.getElementById("msgInput").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendMsg();
      }
    });
  </script>
</body>
</html>
"""

@app.get("/client", response_class=HTMLResponse)
async def client():
    return html_client


# ======================================================================
# 3) Three.js Demo-Client: 1 Cube, Bewegungen werden synchronisiert
# ======================================================================
html_three = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Three.js Sync Cube</title>
  <style>
    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      background: #020617;
      color: #e5e7eb;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }
    header {
      padding: 10px 16px;
      background: #020617;
      border-bottom: 1px solid rgba(30,41,59,0.9);
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 0.85rem;
    }
    header input {
      padding: 5px 8px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.6);
      background: rgba(15,23,42,0.9);
      color: #e5e7eb;
      font-size: 0.8rem;
      outline: none;
    }
    header button {
      border: none;
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 0.8rem;
      cursor: pointer;
      background: #4f46e5;
      color: #e5e7eb;
    }
    header button:hover { background: #6366f1; }
    header span.label {
      color: #9ca3af;
    }
    main {
      flex: 1;
      display: flex;
      flex-direction: row;
      min-height: 0;
    }
    #three-container {
      flex: 2;
      position: relative;
    }
    #three-container canvas {
      display: block;
    }
    #log-panel {
      flex: 1;
      border-left: 1px solid rgba(30,41,59,0.9);
      padding: 10px;
      font-size: 0.8rem;
      background: #020617;
      overflow-y: auto;
    }
    #log-panel h2 {
      margin: 0 0 6px;
      font-size: 0.9rem;
    }
    #log {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    #log li {
      padding: 2px 0;
      border-bottom: 1px solid rgba(31,41,55,0.9);
    }
    .ts { color: #6b7280; margin-right: 4px; }
    .user { font-weight: 600; margin-right: 4px; }
  </style>
</head>
<body>
  <header>
    <span class="label">Room:</span>
    <input id="roomInput" type="text" value="3d" />
    <span class="label">Name:</span>
    <input id="nameInput" type="text" value="Abass" />
    <button id="connectBtn" onclick="connectWS()">Verbinden</button>
    <span id="statusText" style="margin-left:auto;color:#f97316;">● Getrennt</span>
    <span style="color:#9ca3af;">Steuerung: Pfeiltasten bewegen den Würfel</span>
  </header>

  <main>
    <div id="three-container"></div>
    <div id="log-panel">
      <h2>Events</h2>
      <ul id="log"></ul>
    </div>
  </main>

  <!-- three.js von CDN -->
  <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>

  <script>
    let ws = null;
    let username = "Anon";
    let room = "3d";
    let cube = null;
    let scene, camera, renderer;
    let lastSend = 0;

    function logEvent(data) {
      const log = document.getElementById("log");
      const li = document.createElement("li");
      const ts = document.createElement("span");
      ts.className = "ts";
      ts.textContent = "[" + (data.ts || "") + "]";
      const user = document.createElement("span");
      user.className = "user";
      user.textContent = (data.user || "SYSTEM") + ":";
      const text = document.createElement("span");
      text.textContent = " " + (data.text || data.type || "");
      li.appendChild(ts);
      li.appendChild(user);
      li.appendChild(text);
      log.appendChild(li);
      log.scrollTop = log.scrollHeight;
    }

    function setStatus(connected) {
      const s = document.getElementById("statusText");
      if (connected) {
        s.style.color = "#22c55e";
        s.textContent = "● Verbunden (" + username + " @ " + room + ")";
      } else {
        s.style.color = "#f97316";
        s.textContent = "● Getrennt";
      }
    }

    // === THREE.JS SETUP ===
    function initThree() {
      const container = document.getElementById("three-container");
      const w = container.clientWidth || window.innerWidth * 0.6;
      const h = container.clientHeight || (window.innerHeight - 50);

      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x020617);

      camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 100);
      camera.position.set(0, 1.5, 4);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(w, h);
      container.innerHTML = "";
      container.appendChild(renderer.domElement);

      const light = new THREE.DirectionalLight(0xffffff, 1);
      light.position.set(2, 3, 4);
      scene.add(light);
      scene.add(new THREE.AmbientLight(0x404040));

      const grid = new THREE.GridHelper(10, 10);
      scene.add(grid);

      const geom = new THREE.BoxGeometry(1, 1, 1);
      const mat = new THREE.MeshStandardMaterial({ color: 0x4f46e5 });
      cube = new THREE.Mesh(geom, mat);
      cube.position.set(0, 0.5, 0);
      scene.add(cube);

      const loop = () => {
        requestAnimationFrame(loop);
        renderer.render(scene, camera);
      };
      loop();

      window.addEventListener("resize", onResize);
      window.addEventListener("keydown", onKeyDown);
    }

    function onResize() {
      if (!renderer || !camera) return;
      const container = document.getElementById("three-container");
      const w = container.clientWidth || window.innerWidth * 0.6;
      const h = container.clientHeight || (window.innerHeight - 50);
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }

    // Pfeiltasten bewegen den Würfel und senden Bewegung
    function onKeyDown(e) {
      if (!cube) return;
      let moved = false;
      const step = 0.2;
      switch (e.key) {
        case "ArrowUp":
          cube.position.z -= step; moved = true; break;
        case "ArrowDown":
          cube.position.z += step; moved = true; break;
        case "ArrowLeft":
          cube.position.x -= step; moved = true; break;
        case "ArrowRight":
          cube.position.x += step; moved = true; break;
      }
      if (moved) {
        sendObjectTransform();
      }
    }

    // === WEBSOCKET ===
    function connectWS() {
      if (ws && ws.readyState === WebSocket.OPEN) return;

      room = document.getElementById("roomInput").value.trim() || "3d";
      username = document.getElementById("nameInput").value.trim() || "Anon";

      const url = "ws://" + location.host + "/ws/" +
                  encodeURIComponent(room) + "/" +
                  encodeURIComponent(username);
      ws = new WebSocket(url);

      ws.onopen = () => {
        setStatus(true);
        logEvent({ ts: new Date().toISOString(), user: "SYSTEM", text: "WebSocket verbunden" });
      };

      ws.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch (e) {
          console.error("JSON parse error:", event.data);
          return;
        }

        // object_move → Cube aktualisieren
        if (data.type === "object_move" && data.id === "cube-1") {
          // Optional: eigene Nachrichten ignorieren
          if (data.user !== username && cube) {
            const p = data.position || {};
            const r = data.rotation || {};
            cube.position.set(p.x || 0, p.y || 0.5, p.z || 0);
            cube.rotation.set(r.x || 0, r.y || 0, r.z || 0);
          }
        } else {
          // andere Events loggen (join/leave/chat)
          logEvent(data);
        }
      };

      ws.onclose = () => {
        setStatus(false);
        logEvent({ ts: new Date().toISOString(), user: "SYSTEM", text: "Verbindung geschlossen" });
      };

      ws.onerror = () => {
        setStatus(false);
        logEvent({ ts: new Date().toISOString(), user: "SYSTEM", text: "WebSocket Fehler" });
      };
    }

    function sendObjectTransform() {
      if (!ws || ws.readyState !== WebSocket.OPEN || !cube) return;

      const now = Date.now();
      // simple Throttling (max ~20/s)
      if (now - lastSend < 50) return;
      lastSend = now;

      const payload = {
        type: "object_move",
        id: "cube-1",
        position: {
          x: cube.position.x,
          y: cube.position.y,
          z: cube.position.z
        },
        rotation: {
          x: cube.rotation.x,
          y: cube.rotation.y,
          z: cube.rotation.z
        }
      };
      ws.send(JSON.stringify(payload));
    }

    // Init Three.js direkt beim Laden
    window.addEventListener("load", initThree);
  </script>
</body>
</html>
"""

@app.get("/three", response_class=HTMLResponse)
async def three_client():
    return html_three


# ======================================================================
# 4) WebSocket-Endpoint: Rooms + verschiedene Event-Typen
# ======================================================================
@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await websocket.accept()

    room = (room or "lobby").strip()
    username = (username or "Anon").strip()

    if room not in rooms:
        rooms[room] = []

    rooms[room].append((websocket, username))

    # JOIN-Event
    join_msg = {
        "type": "join",
        "user": "SYSTEM",
        "text": f"{username} ist dem Room '{room}' beigetreten",
        "ts": now_ts(),
    }
    for conn, _ in rooms[room]:
        await conn.send_json(join_msg)

    try:
        while True:
            raw = await websocket.receive_text()

            # Versuchen, JSON zu parsen
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Fallback: nur Text → als Chat behandeln
                data = {"type": "chat", "text": raw}

            msg_type = data.get("type", "chat")

            if msg_type == "object_move":
                # Drei.js-Event: Objektbewegung
                msg = {
                    "type": "object_move",
                    "user": username,
                    "id": data.get("id", "cube-1"),
                    "position": data.get("position", {}),
                    "rotation": data.get("rotation", {}),
                    "ts": now_ts(),
                }
            elif msg_type == "chat":
                msg = {
                    "type": "chat",
                    "user": username,
                    "text": data.get("text", ""),
                    "ts": now_ts(),
                }
            else:
                # Unbekannter Typ → als Systemlog
                msg = {
                    "type": msg_type,
                    "user": username,
                    "text": data.get("text", f"Event {msg_type}"),
                    "ts": now_ts(),
                }

            # Broadcast nur in diesem Room
            for conn, _ in rooms[room]:
                await conn.send_json(msg)

    except Exception:
        # Disconnect
        if room in rooms and (websocket, username) in rooms[room]:
            rooms[room].remove((websocket, username))

            leave_msg = {
                "type": "leave",
                "user": "SYSTEM",
                "text": f"{username} hat den Room '{room}' verlassen",
                "ts": now_ts(),
            }
            for conn, _ in rooms.get(room, []):
                await conn.send_json(leave_msg)

            if room in rooms and not rooms[room]:
                del rooms[room]
