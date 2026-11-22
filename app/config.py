import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "tasks.db"))

MCP_SERVER_MODULE = "app.mcp_server.server"