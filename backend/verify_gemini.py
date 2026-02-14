import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(__file__))

# Load env from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app.gemini_agent import chat_with_gemini
from app.models import ChatMessage

async def verify():
    print("Testing Gemini integration...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        return

    print(f"API Key found: {api_key[:5]}...")

    # Mock app state
    app_state = {
        "gtfs": {},
        "predictor": None,
        "alerts": []
    }

    history = [ChatMessage(role="user", content="Hello, are you working?")]
    
    try:
        response = await chat_with_gemini(
            message="Hello, are you working?",
            history=history,
            context=None,
            app_state=app_state
        )
        print("\nResponse received:")
        print(f"Message: {response.message}")
        print(f"Suggested Actions: {response.suggested_actions}")
        print("\nSUCCESS: Gemini integration is working!")
    except Exception as e:
        print(f"\nERROR: Failed to chat with Gemini: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
