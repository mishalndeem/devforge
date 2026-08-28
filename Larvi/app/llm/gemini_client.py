"""
Gemini LLM wrapper for Larvi.

Runs the tool-use loop used by:
- Master Agent
- Email Agent
- Calendar Agent

The existing Larvi agents use a common tool-schema format,
which this wrapper converts to Gemini function declarations.
"""

from typing import Callable

from google import genai
from google.genai import types

from app.config import settings


_client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _build_gemini_tools(tools: list[dict]) -> list[types.Tool]:
    """Convert Larvi's existing tool schemas to Gemini tools."""

    if not tools:
        return []

    declarations = []

    for tool in tools:
        declarations.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=tool.get(
                    "input_schema",
                    {
                        "type": "object",
                        "properties": {},
                    },
                ),
            )
        )

    return [
        types.Tool(
            function_declarations=declarations
        )
    ]


def _build_initial_contents(messages: list[dict]) -> list[types.Content]:
    """
    Convert the initial Larvi message history into Gemini Content objects.

    After the first request we keep Gemini's native Content objects,
    so tool calls and tool responses are preserved correctly.
    """

    contents = []

    for message in messages:
        role = message.get("role", "user")

        if role == "assistant":
            role = "model"

        content = message.get("content", "")

        if isinstance(content, str):
            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part(text=content)
                    ],
                )
            )

    return contents


def run_tool_loop(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    tool_impls: dict[str, Callable],
    max_turns: int = 3,
) -> dict:
    """
    Run Gemini's tool-use loop.

    Returns:
        {
            "final_text": str,
            "tool_calls": [
                {
                    "name": str,
                    "input": dict,
                    "result": object
                }
            ],
            "messages": [...]
        }
    """

    # ---------------------------------------------------------
    # Initial conversation
    # ---------------------------------------------------------

    convo = _build_initial_contents(messages)

    tool_calls_log = []

    gemini_tools = _build_gemini_tools(tools)

    # ---------------------------------------------------------
    # Tool-use loop
    # ---------------------------------------------------------

    for _ in range(max_turns):

        # -----------------------------------------------------
        # Call Gemini
        # -----------------------------------------------------

        try:
            response = _client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=convo,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools if gemini_tools else None,
                    temperature=0.2,
                ),
            )

        except Exception as e:
            error_message = str(e)

            # Handle Gemini free-tier quota errors
            if (
                "RESOURCE_EXHAUSTED" in error_message
                or "429" in error_message
            ):
                return {
                    "final_text": (
                        "Gemini's free-tier quota has been reached. "
                        "Please try again later when the quota resets."
                    ),
                    "tool_calls": tool_calls_log,
                    "messages": messages,
                }

            # Handle all other Gemini API errors
            return {
                "final_text": f"Gemini request failed: {e}",
                "tool_calls": tool_calls_log,
                "messages": messages,
            }

        # -----------------------------------------------------
        # Make sure we have a valid response
        # -----------------------------------------------------

        if not response.candidates:
            return {
                "final_text": "Gemini returned no response.",
                "tool_calls": tool_calls_log,
                "messages": messages,
            }

        candidate = response.candidates[0]

        if not candidate.content:
            return {
                "final_text": "Gemini returned an empty response.",
                "tool_calls": tool_calls_log,
                "messages": messages,
            }

        # -----------------------------------------------------
        # Preserve Gemini's native model response.
        #
        # This contains the function_call parts.
        # -----------------------------------------------------

        convo.append(candidate.content)

        function_calls = []

        for part in candidate.content.parts or []:
            if part.function_call:
                function_calls.append(part.function_call)

        # -----------------------------------------------------
        # No tool call = final answer
        # -----------------------------------------------------

        if not function_calls:
            final_text = response.text or ""

            return {
                "final_text": final_text,
                "tool_calls": tool_calls_log,
                "messages": messages,
            }

        # -----------------------------------------------------
        # Execute every requested tool
        # -----------------------------------------------------

        function_response_parts = []

        for call in function_calls:

            tool_name = call.name

            tool_input = dict(call.args or {})

            fn = tool_impls.get(tool_name)

            # -------------------------------------------------
            # Unknown tool
            # -------------------------------------------------

            if fn is None:
                result = {
                    "success": False,
                    "error": f"Unknown tool '{tool_name}'",
                }

            # -------------------------------------------------
            # Execute actual Python tool
            # -------------------------------------------------

            else:
                try:
                    result = fn(**tool_input)

                except Exception as e:
                    result = {
                        "success": False,
                        "error": (
                            f"Tool '{tool_name}' "
                            f"raised an exception: {e}"
                        ),
                    }

            # -------------------------------------------------
            # Save tool call for Larvi
            # -------------------------------------------------

            tool_calls_log.append(
                {
                    "name": tool_name,
                    "input": tool_input,
                    "result": result,
                }
            )

            # -------------------------------------------------
            # Send the tool result back to Gemini
            # -------------------------------------------------

            function_response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=tool_name,
                        response={
                            "result": result
                        },
                    )
                )
            )

        # -----------------------------------------------------
        # Add all tool results as a single user turn
        # -----------------------------------------------------

        convo.append(
            types.Content(
                role="user",
                parts=function_response_parts,
            )
        )

    # ---------------------------------------------------------
    # Maximum number of turns reached
    # ---------------------------------------------------------

    return {
        "final_text": (
            "I wasn't able to finish that within the allotted "
            "steps. Could you rephrase or simplify the request?"
        ),
        "tool_calls": tool_calls_log,
        "messages": messages,
    }