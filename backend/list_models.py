import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Add backend to path
sys.path.append(os.path.dirname(__file__))

# Load env from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        return

    genai.configure(api_key=api_key)
    print("Available models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
