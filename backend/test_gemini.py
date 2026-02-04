"""Quick test script to verify Gemini API is working."""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print(f"GEMINI_API_KEY set: {'Yes' if os.environ.get('GEMINI_API_KEY') else 'No'}")

if not os.environ.get('GEMINI_API_KEY'):
    print("ERROR: GEMINI_API_KEY is not set in .env")
    sys.exit(1)

# Test the import
try:
    from google import genai
    print("google.genai imported successfully")
except ImportError as e:
    print(f"ERROR importing google.genai: {e}")
    sys.exit(1)

# Test the client
try:
    client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Say "Hello, Gemini is working!" in 5 words or less.'
    )
    print(f"Gemini Response: {response.text}")
    print("\n✅ Gemini API is working correctly!")
except Exception as e:
    print(f"ERROR testing Gemini API: {e}")
    sys.exit(1)
