"""Test script for Finternet API."""
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.payments.services.finternet import FinternetService

print("Testing Finternet Integration...")
print(f"FINTERNET_API_KEY set: {'Yes' if os.environ.get('FINTERNET_API_KEY') else 'No'}")

try:
    service = FinternetService()
    print("Initializing FinternetService... OK")
    
    print("Creating Payment Intent...")
    result = service.create_payment_intent(
        amount="10.00",
        currency="USDC",
        description="Test Payment",
        return_url="http://localhost:5173/payment/callback"
    )
    
    print("\n[SUCCESS] Payment Intent Created Successfully!")
    print(json.dumps(result, indent=2))
    
except Exception as e:
    print(f"\n[ERROR]: {e}")
    import traceback
    traceback.print_exc()
