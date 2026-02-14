import json
import logging
import os
from typing import Optional

from anthropic import AsyncAnthropic

from app.models import ChatMessage, ChatResponse

logger = logging.getLogger("fluxroute.claude")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are FluxRoute Assistant, an AI-powered Toronto transit expert built into the FluxRoute multimodal routing app.

Your role:
- Help users find the best routes across the GTA (Greater Toronto Area)
- Provide real-time transit updates and delay predictions
- Offer tips on cost savings, stress reduction, and schedule optimization
- Be concise, friendly, and practical

Key knowledge:
- TTC subway has 4 lines: Line 1 (Yonge-University, yellow), Line 2 (Bloor-Danforth, green), Line 3 (Scarborough RT, blue, limited service), Line 4 (Sheppard, purple)
- TTC fare is $3.35 flat (2-hour transfer)
- GO Transit serves the broader GTA region
- Rush hours: 7-9 AM and 5-7 PM on weekdays
- Line 1 is the busiest and most delay-prone

You have access to tools to get routes, predict delays, check alerts, and get weather.
Keep responses concise (2-3 sentences max unless the user asks for detail)."""

TOOLS = [
    {
        "name": "get_routes",
        "description": "Get multimodal route options between two locations in Toronto. Returns transit, driving, walking, and hybrid routes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin_lat": {"type": "number", "description": "Origin latitude"},
                "origin_lng": {"type": "number", "description": "Origin longitude"},
                "dest_lat": {"type": "number", "description": "Destination latitude"},
                "dest_lng": {"type": "number", "description": "Destination longitude"},
            },
            "required": ["origin_lat", "origin_lng", "dest_lat", "dest_lng"],
        },
    },
    {
        "name": "predict_delay",
        "description": "Predict delay probability for a TTC subway line at a given time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "line": {"type": "string", "description": "TTC line (e.g. 'Line 1', '1', 'YU')"},
                "hour": {"type": "integer", "description": "Hour of day (0-23)"},
                "day_of_week": {"type": "integer", "description": "Day of week (0=Monday, 6=Sunday)"},
            },
            "required": ["line"],
        },
    },
    {
        "name": "get_service_alerts",
        "description": "Get current TTC service alerts and disruptions.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather conditions in Toronto.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def _execute_tool(tool_name: str, tool_input: dict, app_state: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if tool_name == "get_routes":
            from app.route_engine import generate_routes
            from app.models import Coordinate

            routes = await generate_routes(
                origin=Coordinate(lat=tool_input["origin_lat"], lng=tool_input["origin_lng"]),
                destination=Coordinate(lat=tool_input["dest_lat"], lng=tool_input["dest_lng"]),
                gtfs=app_state.get("gtfs", {}),
                predictor=app_state.get("predictor"),
            )
            # Summarize routes for the model
            summaries = []
            for r in routes:
                summaries.append({
                    "label": r.label,
                    "mode": r.mode.value,
                    "duration_min": r.total_duration_min,
                    "distance_km": r.total_distance_km,
                    "cost": r.cost.total,
                    "delay_prob": r.delay_info.probability,
                    "stress": r.stress_score,
                    "summary": r.summary,
                })
            return json.dumps(summaries, indent=2)

        elif tool_name == "predict_delay":
            predictor = app_state.get("predictor")
            if not predictor:
                return json.dumps({"error": "Predictor not available"})
            result = predictor.predict(
                line=tool_input.get("line", "1"),
                hour=tool_input.get("hour"),
                day_of_week=tool_input.get("day_of_week"),
            )
            return json.dumps(result, indent=2)

        elif tool_name == "get_service_alerts":
            alerts = app_state.get("alerts", [])
            alert_data = [
                {"title": a.title, "description": a.description, "severity": a.severity}
                if hasattr(a, "title") else a
                for a in alerts
            ]
            return json.dumps(alert_data, indent=2)

        elif tool_name == "get_weather":
            from app.weather import get_current_weather
            weather = await get_current_weather()
            return json.dumps(weather, indent=2)

        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return json.dumps({"error": str(e)})


async def chat_with_claude(
    message: str,
    history: list[ChatMessage],
    context: Optional[dict],
    app_state: dict,
) -> ChatResponse:
    """Chat with Claude using tool use for transit queries."""
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-anthropic-api-key-here":
        return ChatResponse(
            message="AI chat is not configured. Please set the ANTHROPIC_API_KEY environment variable to enable the AI assistant.",
            suggested_actions=["Get routes", "Check delays"],
        )

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Build message history
    messages = []
    for msg in history[-10:]:  # Last 10 messages for context
        messages.append({"role": msg.role, "content": msg.content})

    # Add context if available
    user_content = message
    if context:
        user_content = f"{message}\n\n[Current context: {json.dumps(context)}]"

    messages.append({"role": "user", "content": user_content})

    try:
        # Initial API call
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Handle tool use loop (max 3 iterations)
        for _ in range(3):
            if response.stop_reason != "tool_use":
                break

            # Extract tool calls
            tool_results = []
            assistant_content = response.content

            for block in response.content:
                if block.type == "tool_use":
                    result = await _execute_tool(block.name, block.input, app_state)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Send tool results back
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

        # Extract final text
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        # Generate suggested actions based on the conversation
        suggested = _generate_suggestions(message, final_text)

        return ChatResponse(message=final_text, suggested_actions=suggested)

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return ChatResponse(
            message="I'm having trouble connecting to my AI backend. The rest of FluxRoute still works — try using the route planner directly!",
            suggested_actions=["Plan a route", "Check delays", "View alerts"],
        )


def _generate_suggestions(user_msg: str, response: str) -> list[str]:
    """Generate contextual suggested actions."""
    suggestions = []
    lower = user_msg.lower()

    if "delay" in lower or "late" in lower:
        suggestions.extend(["Check Line 1 delays", "View all alerts"])
    elif "route" in lower or "get" in lower or "go" in lower:
        suggestions.extend(["Compare all modes", "Check weather"])
    elif "weather" in lower:
        suggestions.extend(["Plan a route", "Check delays"])
    else:
        suggestions.extend(["Plan a route", "Check delays", "View alerts"])

    return suggestions[:3]
