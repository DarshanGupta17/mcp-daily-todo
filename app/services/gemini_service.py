from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from app.config import APP_TIMEZONE, GEMINI_API_KEY, GEMINI_MODEL
from app.services.event_bus import event_bus, iso_now
from app.services.mcp_client import mcp_client

SYSTEM_INSTRUCTION_TEMPLATE = """You are an AI task management assistant.

You manage the user's daily tasks through the available MCP tools.

You can create, list, update, delete, complete, and reopen tasks.

You MUST use the appropriate tool whenever the user requests an operation that requires reading or modifying tasks.

Never claim that an operation succeeded unless the corresponding MCP tool returned a successful result.

Never invent task IDs.

When modifying an existing task:
- First identify the correct task using list_tasks if its ID is unknown.
- If multiple tasks match, ask the user which one they mean.
- Never modify an ambiguous task.

When a date is not specified, interpret 'today' and 'tomorrow' using the current application date and timezone.

For questions about tasks, use list_tasks instead of guessing.

After executing an operation, provide a short and natural confirmation.

For date ranges, use the appropriate start_date and end_date arguments.

Never perform task modifications directly. Always use the provided tools.

Current application context:
- Timezone: {timezone}
- Today's date: {today}
"""


class GeminiService:
    def __init__(self) -> None:
        self._client: Optional[genai.Client] = None

    def _ensure_client(self) -> genai.Client:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        if self._client is None:
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    def _system_instruction(self) -> str:
        today = datetime.now(ZoneInfo(APP_TIMEZONE)).date().isoformat()
        return SYSTEM_INSTRUCTION_TEMPLATE.format(timezone=APP_TIMEZONE, today=today)

    def _build_tools_config(self) -> types.GenerateContentConfig:
        declarations = mcp_client.mcp_tools_to_gemini()
        function_decls = [
            types.FunctionDeclaration(
                name=d["name"],
                description=d["description"],
                parameters=d["parameters"],
            )
            for d in declarations
        ]
        return types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=function_decls)],
            system_instruction=self._system_instruction(),
        )

    async def chat(
        self,
        user_message: str,
        history: list[dict[str, str]],
        *,
        request_id: str,
    ) -> str:
        client = self._ensure_client()
        config = self._build_tools_config()

        contents: list[types.Content] = []
        for item in history:
            role = "user" if item["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=item["content"])])
            )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )

        await event_bus.emit(
            {
                "event": "chat_status",
                "request_id": request_id,
                "status": "thinking",
                "timestamp": iso_now(),
            }
        )

        max_turns = 12
        for _ in range(max_turns):
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )

            if not response.candidates:
                raise RuntimeError("No response from Gemini")

            candidate = response.candidates[0]
            parts = candidate.content.parts if candidate.content else []

            function_calls = [p.function_call for p in parts if p.function_call]
            if not function_calls:
                text_parts = [p.text for p in parts if p.text]
                final = "\n".join(text_parts).strip() or "Done."
                await event_bus.emit(
                    {
                        "event": "chat_status",
                        "request_id": request_id,
                        "status": "idle",
                        "timestamp": iso_now(),
                    }
                )
                return final

            # Append model turn with function calls
            contents.append(candidate.content)

            response_parts: list[types.Part] = []
            for fc in function_calls:
                name = fc.name
                args = dict(fc.args) if fc.args else {}
                tool_result = await mcp_client.call_tool(
                    name, args, request_id=request_id
                )
                response_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response=tool_result,
                    )
                )

            contents.append(types.Content(role="user", parts=response_parts))

        await event_bus.emit(
            {
                "event": "chat_status",
                "request_id": request_id,
                "status": "idle",
                "timestamp": iso_now(),
            }
        )
        return "I completed the requested operations."


gemini_service = GeminiService()