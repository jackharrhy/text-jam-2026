const boot = window.CHINESE_CHECKERS_BOOT;
const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");
const logEl = document.getElementById("log");
const playersEl = document.getElementById("players");
const identityEl = document.getElementById("identity");
const sessionEl = document.getElementById("session-id");
const turnEl = document.getElementById("turn-status");
const pathEl = document.getElementById("path-readout");
const lobbyPanel = document.getElementById("lobby-panel");
const gamePanel = document.getElementById("game-panel");
const startGameButton = document.getElementById("start-game");
const playerCountSelect = document.getElementById("player-count");
const cpuCountSelect = document.getElementById("cpu-count");

const richColorMap = {
  bright_black: "#606060",
  dodger_blue1: "#00afff",
  dodger_blue2: "#0087d7",
  white: "#f4f4f4",
};

let ws;
let board = {};
let players = [];
let playerConfigs = [];
let sessionId = boot.sessionId || "";
let playerNumber = null;
let currentPlayer = null;
let winner = null;
let cursor = null;
let selectedPath = [];
let hoverCoord = null;
let layout = new Map();
let playerId = localStorage.getItem("cc_player_id");
let lobbyNumPlayers = 2;
let lobbyCpuCount = 0;
let inGame = false;

if (!playerId) {
  playerId = randomPlayerId();
  localStorage.setItem("cc_player_id", playerId);
}

connect();
draw();

document.getElementById("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;
  send({ type: "chat", message });
  input.value = "";
});

startGameButton.addEventListener("click", () => {
  send({ type: "start_game", cpu_count: lobbyCpuCount });
});

playerCountSelect.addEventListener("change", () => {
  lobbyNumPlayers = Number(playerCountSelect.value);
  send({ type: "update_num_players", num_players: lobbyNumPlayers });
  renderPlayers();
});

cpuCountSelect.addEventListener("change", () => {
  lobbyCpuCount = Number(cpuCountSelect.value);
  renderPlayers();
});

document.getElementById("clear-path").addEventListener("click", () => {
  selectedPath = [];
  updatePath();
  draw();
});

document.getElementById("send-move").addEventListener("click", () => {
  if (selectedPath.length < 2) {
    writeLog("system", "select at least a piece and a destination");
    return;
  }
  send({ type: "move", path: selectedPath });
  selectedPath = [];
  updatePath();
});

document.getElementById("cycle-piece").addEventListener("click", () => {
  if (boot.spectator) return;

  const mine = myPieces();
  if (!mine.length) return;
  const index = cursor ? mine.findIndex((coord) => sameCoord(coord, cursor)) : -1;
  cursor = mine[(index + 1) % mine.length];
  draw();
});

canvas.addEventListener("mousemove", (event) => {
  hoverCoord = coordFromEvent(event);
  draw();
});

canvas.addEventListener("mouseleave", () => {
  hoverCoord = null;
  draw();
});

canvas.addEventListener("click", (event) => {
  const coord = coordFromEvent(event);
  if (!coord) return;
  cursor = coord;

  if (boot.spectator) {
    draw();
    return;
  }

  selectedPath.push(coord);
  updatePath();
  send({ type: "validate_partial", path: selectedPath });
  draw();
});

function connect() {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${scheme}://${location.host}/ws`);

  ws.addEventListener("open", () => {
    send({
      type: "connect",
      protocol_version: 2,
      player_id: playerId,
      name: boot.name,
      session_id: sessionId || undefined,
      num_players: sessionId ? undefined : 2,
      spectator: Boolean(boot.spectator),
    });
  });

  ws.addEventListener("message", (event) => {
    handleMessage(JSON.parse(event.data));
  });

  ws.addEventListener("close", () => {
    turnEl.textContent = "disconnected";
    writeLog("system", "websocket closed");
  });
}

function handleMessage(msg) {
  if (msg.type === "welcome") {
    sessionId = msg.session_id;
    playerNumber = msg.player_number ?? playerNumber;
    sessionEl.textContent = sessionId;
    history.replaceState(
      null,
      "",
      `/game?name=${encodeURIComponent(boot.name)}&session_id=${encodeURIComponent(sessionId)}${boot.spectator ? "&spectator=1" : ""}`,
    );
    writeLog("system", `welcome to session ${sessionId}`);
    for (const chat of msg.chat_history ?? []) printChat(chat);
  } else if (msg.type === "session_validated") {
    playerNumber = msg.player_num ?? playerNumber;
    playerConfigs = msg.player_configs ?? [];
    lobbyNumPlayers = msg.num_players ?? lobbyNumPlayers;
    playerCountSelect.value = String(lobbyNumPlayers);
    if (msg.session_state === "in_progress") showGame();
  } else if (msg.type === "lobby_state") {
    sessionId = msg.session_id;
    players = msg.players;
    lobbyNumPlayers = msg.num_players ?? lobbyNumPlayers;
    playerCountSelect.value = String(lobbyNumPlayers);
    sessionEl.textContent = sessionId;
    showLobby();
    renderPlayers();
  } else if (msg.type === "game_started") {
    playerNumber = msg.player_number;
    playerConfigs = msg.player_configs;
    showGame();
  } else if (msg.type === "game_state") {
    board = msg.board;
    currentPlayer = msg.current_player;
    winner = msg.winner;
    showGame();
    renderIdentity();
    draw();
  } else if (msg.type === "chat") {
    printChat(msg);
  } else if (msg.type === "player_joined_game") {
    writeLog("chat", `${msg.player_name} has joined the game!`);
  } else if (msg.type === "player_reconnected") {
    writeLog("chat", `${msg.player_name} reconnected to the game.`);
  } else if (msg.type === "player_disconnected") {
    writeLog("chat", `${msg.player_name} disconnected from the game.`);
  } else if (msg.type === "player_quit") {
    writeLog("chat", `${msg.player_name} quit the game.`);
  } else if (msg.type === "partial_validation") {
    if (!msg.valid) {
      writeLog("invalid", msg.message || "invalid selection");
      selectedPath.pop();
      updatePath();
      draw();
    }
  } else if (msg.type === "error") {
    writeLog("error", msg.message);
  } else if (msg.type !== "server_heartbeat") {
    writeLog("server", JSON.stringify(msg));
  }
}

function send(message) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify(message));
}

function draw() {
  const width = canvas.width;
  const height = canvas.height;
  ctx.fillStyle = "#0d0d0d";
  ctx.fillRect(0, 0, width, height);
  ctx.font = "20px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  layout = new Map();

  const cellX = Math.min(28, (width - 48) / 26);
  const cellY = Math.min(30, (height - 48) / Math.max(1, boot.rows.length - 1));
  const radius = Math.max(8, Math.min(13, cellX * 0.42));
  const boardWidth = 24 * cellX;
  const boardHeight = (boot.rows.length - 1) * cellY;
  const originX = (width - boardWidth) / 2;
  const originY = (height - boardHeight) / 2;

  for (let rowIndex = 0; rowIndex < boot.rows.length; rowIndex++) {
    const row = boot.rows[rowIndex];
    const y = originY + rowIndex * cellY;

    for (let tileIndex = 0; tileIndex < row.tiles.length; tileIndex++) {
      const coord = row.tiles[tileIndex];
      const key = coordKey(coord);
      const x = originX + (row.spacing + tileIndex * 2) * cellX;
      layout.set(key, { x, y, radius });

      const zone = zoneForCoord(coord);
      if (zone) {
        ctx.fillStyle = cssColor(boot.colors[zone].zone);
        ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
      }

      if (sameCoord(coord, hoverCoord) || sameCoord(coord, cursor)) {
        ctx.strokeStyle = "#f4f4f4";
        ctx.lineWidth = 2;
        ctx.strokeRect(x - radius - 2, y - radius - 2, radius * 2 + 4, radius * 2 + 4);
      }

      if (selectedPath.some((pathCoord) => sameCoord(pathCoord, coord))) {
        ctx.fillStyle = "#7f7f7f";
        ctx.fillRect(x - radius - 1, y - radius - 1, radius * 2 + 2, radius * 2 + 2);
      }

      const occupant = board[key];
      ctx.fillStyle = occupant == null ? "#e8e8e8" : pieceColor(occupant);
      ctx.fillText(occupant == null ? "○" : "●", x, y + 1);
    }
  }

  turnEl.textContent = winner
    ? `winner: player ${winner}`
    : currentPlayer
      ? `turn: player ${currentPlayer}${currentPlayer === playerNumber ? " (you)" : ""}${boot.spectator ? " // spectator" : ""}`
      : "lobby";
}

function coordFromEvent(event) {
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * canvas.width;
  const y = ((event.clientY - rect.top) / rect.height) * canvas.height;
  let closest = null;
  let closestDistance = Infinity;

  for (const [key, point] of layout.entries()) {
    const distance = Math.hypot(point.x - x, point.y - y);
    if (distance < closestDistance && distance <= point.radius + 12) {
      closest = key.split(",").map(Number);
      closestDistance = distance;
    }
  }

  return closest;
}

function renderPlayers() {
  const connectedPlayers = players.filter((player) => player.connected).length;
  const totalPlayers = connectedPlayers + lobbyCpuCount;
  const isHost = players.some((player) => player.player_id === playerId && player.is_host);
  const allConnected = players.every((player) => player.connected);

  playersEl.replaceChildren();

  if (players.length) {
    for (const player of players) {
      playersEl.append(renderPlayerRow(player));
    }
  } else {
    const row = document.createElement("div");
    row.textContent = "Waiting for server...";
    playersEl.append(row);
  }

  const ready = isHost && totalPlayers === lobbyNumPlayers && allConnected;
  startGameButton.disabled = !ready;
  playerCountSelect.disabled = !isHost || inGame;
  cpuCountSelect.disabled = !isHost || inGame;

  if (ready) {
    turnEl.textContent = "Ready to start game";
  } else if (totalPlayers > lobbyNumPlayers) {
    turnEl.textContent = "Too many players...";
  } else if (isHost) {
    turnEl.textContent = "Waiting for players...";
  } else {
    turnEl.textContent = "Waiting for host...";
  }

  renderIdentity();
}

function renderPlayerRow(player) {
  const connected = player.connected ? "connected" : "disconnected";
  const statusClass = player.connected ? "player-online" : "player-offline";

  const row = document.createElement("div");
  row.append(document.createTextNode(`${player.name} `));

  const status = document.createElement("span");
  status.className = statusClass;
  status.textContent = `(${connected})`;
  row.append(status);

  const extra = document.createElement("span");
  extra.className = "player-extra";
  extra.textContent = `${player.is_host ? " (host)" : ""}${player.is_cpu ? " (cpu)" : ""}`;
  row.append(extra);

  return row;
}

function renderIdentity() {
  identityEl.textContent = boot.spectator
    ? `you: ${boot.name} // spectator`
    : `you: ${boot.name} // player ${playerNumber ?? "?"}`;
}

function printChat(msg) {
  const name = msg.player_name ?? "chat";
  writeLog("chat", `${name}: ${msg.message ?? ""}`);
}

function writeLog(source, message) {
  const line = document.createElement("div");
  line.className = `log-line ${source}`;
  line.textContent = source === "chat" ? message : `[${source}] ${message}`;
  logEl.append(line);
  logEl.scrollTop = logEl.scrollHeight;
}

function showLobby() {
  inGame = false;
  lobbyPanel.hidden = false;
  gamePanel.hidden = true;
}

function showGame() {
  inGame = true;
  lobbyPanel.hidden = true;
  gamePanel.hidden = false;
}

function updatePath() {
  pathEl.textContent = selectedPath.length
    ? `path: ${selectedPath.map((coord) => `(${coord[0]},${coord[1]})`).join(" -> ")}`
    : "path: empty";
}

function myPieces() {
  if (!playerNumber || boot.spectator) return [];
  return Object.entries(board)
    .filter(([, occupant]) => occupant === playerNumber)
    .map(([key]) => key.split(",").map(Number));
}

function pieceColor(player) {
  const config = playerConfigs.find((item) => item.player === player);
  return cssColor(config?.piece ?? "white");
}

function zoneForCoord(coord) {
  for (const [zone, coords] of Object.entries(boot.homeZones)) {
    if (coords.some((item) => sameCoord(item, coord))) return zone;
  }
  return null;
}

function cssColor(color) {
  return richColorMap[color] ?? color;
}

function coordKey(coord) {
  return `${coord[0]},${coord[1]}`;
}

function sameCoord(a, b) {
  return Boolean(a && b && a[0] === b[0] && a[1] === b[1]);
}

function randomPlayerId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  const bytes = new Uint8Array(16);

  if (window.crypto?.getRandomValues) {
    window.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i++) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }

  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, "0"));

  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex
    .slice(6, 8)
    .join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}
