import json
import logging
import os
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from app.models import ChatMessage, ChatResponse

logger = logging.getLogger("fluxroute.gemini")

def _get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are FluxRoute Assistant, an AI-powered Toronto transit expert built into the FluxRoute multimodal routing app.

Your role:
- Help users find the best routes across the GTA (Greater Toronto Area)
- Provide real-time transit updates and delay predictions
- Offer tips on cost savings, stress reduction, and schedule optimization
- Be concise, friendly, and practical

Key knowledge:
- TTC rapid transit has 5 lines: Line 1 (Yonge-University, yellow subway), Line 2 (Bloor-Danforth, green subway), Line 4 (Sheppard, purple subway), Line 5 (Eglinton Crosstown, orange LRT), Line 6 (Finch West, brown LRT)
- Line 3 (Scarborough RT) permanently closed Nov 2023, replaced by bus shuttle
- TTC fare is $3.35 flat (2-hour transfer)
- GO Transit, YRT, MiWay, and Brampton Transit also serve the broader GTA region
- Rush hours: 7-9 AM and 5-7 PM on weekdays
- Line 1 is the busiest and most delay-prone

You have access to tools to get routes, predict delays, check alerts, and get weather.
Keep responses concise (2-3 sentences max unless the user asks for detail)."""

# Tool definitions adapted for Gemini
tools_definitions = [
    {
        "name": "get_routes",
        "description": "Get multimodal route options between two locations in Toronto. Returns transit, driving, walking, and hybrid routes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin_lat": {"type": "NUMBER", "description": "Origin latitude"},
                "origin_lng": {"type": "NUMBER", "description": "Origin longitude"},
                "dest_lat": {"type": "NUMBER", "description": "Destination latitude"},
                "dest_lng": {"type": "NUMBER", "description": "Destination longitude"},
            },
            "required": ["origin_lat", "origin_lng", "dest_lat", "dest_lng"],
        },
    },
    {
        "name": "predict_delay",
        "description": "Predict delay probability for a TTC subway line at a given time.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "line": {"type": "STRING", "description": "TTC line (e.g. 'Line 1', '1', 'YU')"},
                "hour": {"type": "INTEGER", "description": "Hour of day (0-23)"},
                "day_of_week": {"type": "INTEGER", "description": "Day of week (0=Monday, 6=Sunday)"},
            },
            "required": ["line"],
        },
    },
    {
        "name": "get_service_alerts",
        "description": "Get current TTC service alerts and disruptions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather conditions in Toronto.",
        "parameters": {
            "type": "OBJECT",
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

            # Sanitize inputs (Gemini sometimes passes strings for numbers)
            try:
                origin_lat = float(tool_input["origin_lat"])
                origin_lng = float(tool_input["origin_lng"])
                dest_lat = float(tool_input["dest_lat"])
                dest_lng = float(tool_input["dest_lng"])
            except (ValueError, TypeError):
                 return json.dumps({"error": "Invalid coordinates provided"})

            routes = await generate_routes(
                origin=Coordinate(lat=origin_lat, lng=origin_lng),
                destination=Coordinate(lat=dest_lat, lng=dest_lng),
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
                hour=int(tool_input.get("hour")) if tool_input.get("hour") is not None else None,
                day_of_week=int(tool_input.get("day_of_week")) if tool_input.get("day_of_week") is not None else None,
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


async def chat_with_gemini(
    message: str,
    history: list[ChatMessage],
    context: Optional[dict],
    app_state: dict,
) -> ChatResponse:
    """Chat with Gemini using tool use for transit queries."""
    api_key = _get_gemini_api_key()
    if not api_key or api_key == "your-api-key-here":
        return ChatResponse(
            message="AI chat is not configured. Please set the GEMINI_API_KEY environment variable to enable the AI assistant.",
            suggested_actions=["Get routes", "Check delays"],
        )

    try:
        genai.configure(api_key=api_key)
        
        # Initialize model with tools
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=SYSTEM_PROMPT,
            tools=tools_definitions
        )

        # Build chat history
        chat_history = []
        for msg in history[-10:]:
            role = "user" if msg.role == "user" else "model"
            chat_history.append({"role": role, "parts": [msg.content]})

        # Add context if available
        user_content = message
        if context:
            user_content = f"{message}\n\n[Current context: {json.dumps(context)}]"

        chat = model.start_chat(history=chat_history)
        
        # Send message
        response = chat.send_message(user_content)
        
        # Handle tool calls
        # Gemini handles the loop implicitly if we use automatic function calling, 
        # but here we are using the manual approach or we need to handle the response parts.
        # Actually, with the 'tools' parameter, Gemini returns a function call part.
        
        final_text = ""
        function_calls_made = False

        # We need to handle potential multiple turns of tool use
        # The Python SDK's automatic function calling (enable_automatic_function_calling=True) 
        # would need the actual functions to be passed. Since we have _execute_tool, 
        # we might need to handle the parts manually.
        
        current_response = response
        
        # Simple loop for tool execution (Gemini 1.5 style)
        for _ in range(3):
            part = current_response.candidates[0].content.parts[0]
            
            if part.function_call:
                function_calls_made = True
                tool_name = part.function_call.name
                tool_args = dict(part.function_call.args)
                
                logger.info(f"Gemini requested tool: {tool_name}")
                
                tool_result = await _execute_tool(tool_name, tool_args, app_state)
                
                # Send result back to model
                current_response = chat.send_message(
                    genai.protos.Content(
                        parts=[genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={'result': tool_result}
                            )
                        )]
                    )
                )
            else:
                # Text response
                final_text = current_response.text
                break

        if not final_text and function_calls_made:
             # If we ended after tool calls without text (unlikely with loop break), get default
             if current_response.text:
                 final_text = current_response.text
        
        if not final_text:
            final_text = current_response.text

        # Generate suggested actions
        suggested = _generate_suggestions(message, final_text)

        return ChatResponse(message=final_text, suggested_actions=suggested)

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
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
