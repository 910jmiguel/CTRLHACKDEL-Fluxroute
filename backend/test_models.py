import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Add backend to path
sys.path.append(os.path.dirname(__file__))

# Load env from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def test_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        return

    genai.configure(api_key=api_key)
    
    models_to_test = [
        'gemini-2.0-flash',
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-flash-latest',
        'gemini-pro'
    ]
    
    print(f"Testing models with key: {api_key[:5]}...")
    
    for model_name in models_to_test:
        print(f"\nTesting {model_name}...")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello")
            print(f"SUCCESS: {model_name} responded: {response.text[:20]}...")
            return  # Stop after first success
        except Exception as e:
            print(f"FAILED: {model_name} - {e}")

if __name__ == "__main__":
    test_models()
