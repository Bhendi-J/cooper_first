"""Test script to verify Finternet API connection."""
import os
import requests
import json

# Load API key from environment or use a test key
API_KEY = os.environ.get("FINTERNET_API_KEY", "")
BASE_URL = "https://api.fmm.finternetlab.io/api/v1"

def test_create_payment_intent():
    """Test creating a payment intent with Finternet API."""
    
    if not API_KEY:
        print("[ERROR] FINTERNET_API_KEY not set!")
        print("   Please set the environment variable or add it to .env")
        return None
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": "0.01",
        "currency": "USD",
        "type": "DELIVERY_VS_PAYMENT",
        "settlementMethod": "OFF_RAMP_MOCK",
        "settlementDestination": "bank_account_123",
        "description": "Cooper Test Payment"
    }
    
    print("=" * 50)
    print("Testing Finternet API - Create Payment Intent")
    print("=" * 50)
    print(f"URL: {BASE_URL}/payment-intents")
    print(f"API Key: {API_KEY[:15]}...{API_KEY[-4:]}" if len(API_KEY) > 19 else f"API Key: {API_KEY}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)
    
    try:
        response = requests.post(
            f"{BASE_URL}/payment-intents",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print("-" * 50)
        
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            print("[SUCCESS!]")
            print(f"Response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"[ERROR] Status: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"[CONNECTION ERROR] {e}")
        return None
    except requests.exceptions.Timeout:
        print("[TIMEOUT] Request took too long")
        return None
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}")
        return None


if __name__ == "__main__":
    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        API_KEY = os.environ.get("FINTERNET_API_KEY", "")
    except ImportError:
        pass
    
    result = test_create_payment_intent()
    
    if result:
        print("\n" + "=" * 50)
        print("Payment Intent created successfully!")
        data = result.get('data', result)
        print(f"Intent ID: {data.get('id')}")
        payment_url = data.get('paymentUrl')
        if payment_url:
            print(f"Payment URL: {payment_url}")
        print("=" * 50)

