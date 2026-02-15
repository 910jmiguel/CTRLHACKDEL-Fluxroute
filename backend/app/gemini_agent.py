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
- Recommend optimal park-and-ride (hybrid) routes, analyzing parking, service schedules, and disruptions
- Offer tips on cost savings, stress reduction, and schedule optimization
- Be concise, friendly, and practical

Key knowledge:
- TTC rapid transit has 5 lines: Line 1 (Yonge-University, yellow subway), Line 2 (Bloor-Danforth, green subway), Line 4 (Sheppard, purple subway), Line 5 (Eglinton Crosstown, orange LRT), Line 6 (Finch West, brown LRT)
- Line 3 (Scarborough RT) permanently closed Nov 2023, replaced by bus shuttle
- TTC fare is $3.35 flat (2-hour transfer). TTC parking lots are free.
- GO Transit: distance-based fares ($4-$12), parking $4/day at most GO stations
- GO trains have limited weekend service — many lines don't run on weekends
- TTC subway runs all day, every day (5:30 AM - 1:30 AM, later on weekends)
- Rush hours: 7-9 AM and 5-7 PM on weekdays
- Line 1 is the busiest and most delay-prone
- Park-and-ride is ideal for suburban commuters: drive to a station with free parking, take transit downtown

You have access to tools to get routes, predict delays, check alerts, get weather, and analyze hybrid/park-and-ride options.
When users ask about commuting from suburbs (Richmond Hill, Markham, Scarborough, Mississauga, etc.), proactively suggest park-and-ride options with specific station recommendations.

IMPORTANT — Fact-checking responsibilities:
- Always use the get_service_alerts tool to verify active closures and disruptions before recommending a transit line. NEVER recommend a line that has an active closure.
- Always use get_hybrid_stations to verify parking availability before suggesting a park-and-ride station. Do not assume parking exists — confirm it.
- On weekends and late nights, warn users that GO Transit service is limited or non-existent. Use recommend_hybrid_route which checks schedules automatically.
- Cross-reference delay predictions with service alerts — if a line shows high delay AND has active alerts, strongly recommend alternatives.
- When giving schedule info, note that GTFS schedules are the source of truth. If unsure, say so and suggest checking the TTC/GO website.

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
    {
        "name": "get_hybrid_stations",
        "description": "Find park-and-ride stations near a location. Returns TTC subway and GO Transit stations with parking availability, daily rates, capacity, and distance. Use this when users ask about park-and-ride, commuting from suburbs, or hybrid driving+transit options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "lat": {"type": "NUMBER", "description": "Latitude of the starting location"},
                "lng": {"type": "NUMBER", "description": "Longitude of the starting location"},
                "radius_km": {"type": "NUMBER", "description": "Search radius in km (default 20)"},
            },
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "recommend_hybrid_route",
        "description": "Analyze and recommend the best park-and-ride option for a trip. Considers service alerts, time of day, parking, GO weekend schedules, and traffic. Returns a detailed recommendation with reasoning.",
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
        "name": "check_station_schedule",
        "description": "Check upcoming departures from a specific transit station. Verifies if a line is currently running. Use this to fact-check whether a GO train or TTC subway is actually running at the current time before recommending it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "station_name": {"type": "STRING", "description": "Name of the station (e.g. 'Finch', 'Richmond Hill GO')"},
            },
            "required": ["station_name"],
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

        elif tool_name == "get_hybrid_stations":
            from app.parking_data import find_stations_with_parking
            from app.gtfs_parser import find_nearest_rapid_transit_stations

            lat = float(tool_input["lat"])
            lng = float(tool_input["lng"])
            radius = float(tool_input.get("radius_km", 20))

            # Get stations with parking from hardcoded DB
            parking_stations = find_stations_with_parking(lat, lng, radius_km=radius)

            # Also get rapid transit stations from GTFS
            gtfs = app_state.get("gtfs", {})
            rapid = find_nearest_rapid_transit_stations(gtfs, lat, lng, radius_km=radius, limit=15)

            # Merge parking info into rapid transit results
            from app.parking_data import get_parking_info
            stations = []
            seen = set()

            for s in parking_stations:
                name = s["station_name"]
                if name in seen:
                    continue
                seen.add(name)
                stations.append({
                    "station": name,
                    "distance_km": round(s["distance_km"], 1),
                    "agency": s.get("agency", "TTC"),
                    "parking_rate": f"Free" if s.get("daily_rate", 0) == 0 else f"${s['daily_rate']}/day",
                    "capacity": s.get("capacity", 0),
                    "lot_type": s.get("type", "surface"),
                })

            for s in rapid:
                name = s["stop_name"]
                if name in seen:
                    continue
                seen.add(name)
                parking = get_parking_info(name)
                stations.append({
                    "station": name,
                    "distance_km": round(s["distance_km"], 1),
                    "line": s.get("line", ""),
                    "agency": "TTC",
                    "has_parking": parking is not None,
                    "parking_rate": f"Free" if parking and parking.get("daily_rate", 0) == 0 else (f"${parking['daily_rate']}/day" if parking else "No parking lot"),
                })

            stations.sort(key=lambda x: x["distance_km"])
            return json.dumps(stations[:15], indent=2)

        elif tool_name == "recommend_hybrid_route":
            from app.route_engine import generate_routes
            from app.models import Coordinate, RouteMode
            from datetime import datetime

            origin = Coordinate(
                lat=float(tool_input["origin_lat"]),
                lng=float(tool_input["origin_lng"]),
            )
            dest = Coordinate(
                lat=float(tool_input["dest_lat"]),
                lng=float(tool_input["dest_lng"]),
            )

            # Generate routes with hybrid mode
            routes = await generate_routes(
                origin=origin,
                destination=dest,
                gtfs=app_state.get("gtfs", {}),
                predictor=app_state.get("predictor"),
                modes=[RouteMode.HYBRID, RouteMode.DRIVING, RouteMode.TRANSIT],
                app_state=app_state,
            )

            now = datetime.now()
            is_weekend = now.weekday() >= 5

            # Build detailed analysis
            analysis = {
                "time": now.strftime("%H:%M %A"),
                "is_weekend": is_weekend,
                "is_rush_hour": 7 <= now.hour <= 9 or 17 <= now.hour <= 19,
                "options": [],
            }

            # Check service alerts
            alerts = app_state.get("alerts", [])
            active_alerts = []
            for a in alerts:
                if hasattr(a, "active") and a.active and a.severity in ("warning", "error"):
                    active_alerts.append(a.title)
                elif isinstance(a, dict) and a.get("active") and a.get("severity") in ("warning", "error"):
                    active_alerts.append(a.get("title", ""))
            if active_alerts:
                analysis["active_disruptions"] = active_alerts

            for r in routes:
                opt = {
                    "label": r.label,
                    "mode": r.mode.value,
                    "duration_min": r.total_duration_min,
                    "cost": r.cost.total,
                    "delay_probability": r.delay_info.probability,
                    "stress_score": r.stress_score,
                    "summary": r.summary,
                }
                if r.parking_info:
                    opt["parking"] = {
                        "station": r.parking_info.station_name,
                        "rate": "Free" if r.parking_info.daily_rate == 0 else f"${r.parking_info.daily_rate}/day",
                        "capacity": r.parking_info.capacity,
                        "agency": r.parking_info.agency,
                    }
                if r.traffic_summary:
                    opt["traffic"] = r.traffic_summary
                analysis["options"].append(opt)

            if is_weekend:
                analysis["note"] = "Weekend: GO Transit has limited service. TTC subway stations recommended for park-and-ride."

            return json.dumps(analysis, indent=2)

        elif tool_name == "check_station_schedule":
            from app.gtfs_parser import get_next_departures
            from app.parking_data import get_parking_info
            from datetime import datetime

            station_name = tool_input.get("station_name", "")
            gtfs = app_state.get("gtfs", {})
            now = datetime.now()

            # Find the stop by name search
            stops_df = gtfs.get("stops")
            if stops_df is None:
                return json.dumps({"error": "GTFS data not loaded"})

            # Search for matching stops
            name_lower = station_name.lower()
            matches = stops_df[stops_df["stop_name"].str.lower().str.contains(name_lower, na=False)]

            if matches.empty:
                return json.dumps({
                    "station": station_name,
                    "found": False,
                    "message": f"Station '{station_name}' not found in GTFS data. It may be a GO Transit station not in the TTC feed.",
                })

            # Get departures for the first matching stop
            stop_id = str(matches.iloc[0]["stop_id"])
            stop_name_found = matches.iloc[0]["stop_name"]

            departures = get_next_departures(gtfs, stop_id, limit=5)

            # Get parking info
            parking = get_parking_info(station_name)

            # Check alerts for this station
            alerts = app_state.get("alerts", [])
            station_alerts = []
            for a in alerts:
                title = a.title if hasattr(a, "title") else a.get("title", "")
                if station_name.lower() in title.lower():
                    station_alerts.append(title)

            result = {
                "station": stop_name_found,
                "found": True,
                "current_time": now.strftime("%H:%M %A"),
                "is_weekend": now.weekday() >= 5,
                "upcoming_departures": departures[:5] if departures else [],
                "service_running": len(departures) > 0,
                "parking": {
                    "available": parking is not None,
                    "rate": f"Free" if parking and parking.get("daily_rate", 0) == 0 else (f"${parking['daily_rate']}/day" if parking else "N/A"),
                    "capacity": parking.get("capacity", 0) if parking else 0,
                } if parking else {"available": False},
            }

            if station_alerts:
                result["active_alerts"] = station_alerts

            if not departures:
                result["note"] = f"No upcoming departures found for {stop_name_found}. The line may not be running at this time."

            return json.dumps(result, indent=2)

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
    elif "hybrid" in lower or "park" in lower or "ride" in lower:
        suggestions.extend(["Find parking stations", "Compare all modes", "Check GO schedules"])
    elif "route" in lower or "get" in lower or "go" in lower:
        suggestions.extend(["Compare all modes", "Find park & ride", "Check weather"])
    elif "weather" in lower:
        suggestions.extend(["Plan a route", "Check delays"])
    elif "commut" in lower or "suburb" in lower:
        suggestions.extend(["Find park & ride", "Compare all modes", "Check delays"])
    else:
        suggestions.extend(["Plan a route", "Find park & ride", "Check delays"])

    return suggestions[:3]
