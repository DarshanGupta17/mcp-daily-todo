const listeners = new Set();

let socket = null;
let reconnectTimer = null;

export function onWsEvent(handler) {
  listeners.add(handler);
  return () => listeners.delete(handler);
}

function emit(data) {
  listeners.forEach((fn) => fn(data));
}

export function connectWebSocket() {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${window.location.host}/ws`;

  socket = new WebSocket(url);

  socket.onopen = () => {
    emit({ event: "ws_connected" });
  };

  socket.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      emit(data);
    } catch (_) {
      /* ignore */
    }
  };

  socket.onclose = () => {
    emit({ event: "ws_disconnected" });
    reconnectTimer = setTimeout(connectWebSocket, 2000);
  };

  socket.onerror = () => {
    socket.close();
  };
}

export function disconnectWebSocket() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  if (socket) socket.close();
}