import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.gemini_service import gemini_service
from app.services.mcp_client import mcp_client

router = APIRouter(prefix="/api")

_chat_lock = asyncio.Lock()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    request_id: str | None = None


class ChatResponse(BaseModel):
    request_id: str
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def post_chat(body: ChatRequest) -> ChatResponse:
    if not mcp_client.connected:
        raise HTTPException(status_code=503, detail="MCP server is not connected")

    request_id = body.request_id or str(uuid4())

    async with _chat_lock:
        try:
            history = [h.model_dump() for h in body.history]
            reply = await gemini_service.chat(
                body.message, history, request_id=request_id
            )
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini error: {e}") from e

    return ChatResponse(request_id=request_id, reply=reply)