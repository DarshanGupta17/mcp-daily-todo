from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, tasks, websocket
from app.database.database import init_db
from app.services.mcp_client import mcp_client

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    websocket.setup_event_bridge()
    try:
        await mcp_client.connect()
    except Exception as e:
        print(f"MCP connection failed: {e}")
    await websocket.broadcast_snapshot()
    yield
    await mcp_client.disconnect()


app = FastAPI(title="MCP Playground", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(websocket.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mcp_connected": mcp_client.connected,
        "tools": len(mcp_client.tools),
    }