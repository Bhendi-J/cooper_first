"""
Gemini OCR Service for receipt parsing.
Uses Google's Gemini API to extract structured data from receipt images.
"""
import os
from typing import Dict, Any
import json

# Use the google-genai library (newer SDK)
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-genai not installed. OCR features disabled.")

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. OCR features disabled.")


class GeminiOCRService:
    """Service for parsing receipts using Google Gemini vision models."""
    
    def __init__(self):
        self.client = None
        if not GEMINI_AVAILABLE:
            print("Warning: Gemini SDK not available")
            return
        
        # Check both environment variable names
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables.")
        else:
            try:
                self.client = genai.Client(api_key=api_key)
                print("Gemini OCR service initialized")
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini client: {e}")

    def is_available(self) -> bool:
        """Check if OCR service is available."""
        return self.client is not None and GEMINI_AVAILABLE and PIL_AVAILABLE

    def parse_receipt(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Parses a receipt image using Gemini and returns structured data.
        
        Returns:
            Dict with keys: amount, currency, description, date, items, category
        """
        if not self.is_available():
            return {"error": "Gemini OCR service not available"}

        if not PIL_AVAILABLE:
            return {"error": "Pillow not installed"}

        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            prompt = """
            Analyze this receipt image and extract the following information in JSON format:
            - amount: The total amount (numeric only, no currency symbols). Use the final/grand total.
            - currency: The currency code (e.g., USD, INR, EUR).
            - description: A brief description of the purchase (e.g., "Restaurant bill", "Grocery shopping").
            - date: The date of purchase in YYYY-MM-DD format. If not visible, use null.
            - merchant: The store/merchant name if visible.
            - category: Categorize as one of: food, transport, entertainment, shopping, utilities, health, travel, other
            - items: A list of items purchased, each with 'name' and 'price' (numeric).
            
            Return ONLY the JSON object, no markdown formatting or explanation.
            If you cannot read the receipt clearly, still provide your best estimate with available info.
            """

            # Try different model names with the new google-genai SDK
            # Updated based on available models from the API
            models_to_try = [
                'gemini-2.0-flash',
                'gemini-2.0-flash-lite-001',
                'gemini-flash-latest', 
                'gemini-pro-latest',
                'gemini-1.5-flash', # Keeping as fallback
            ]
            
            response = None
            last_error = None
            
            for model_name in models_to_try:
                try:
                    print(f"Trying model: {model_name}")
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[prompt, image]
                    )
                    if response and response.text:
                        print(f"Success with model: {model_name}")
                        break
                except Exception as e:
                    last_error = e
                    print(f"Model {model_name} failed: {str(e)[:100]}")
                    continue
            
            if not response or not response.text:
                if last_error:
                    return {"error": f"Failed to parse receipt: {str(last_error)[:200]}"}
                return {"error": "No response from Gemini"}
            
            # Clean up response text if it contains markdown code blocks
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.startswith("```"):
                text_response = text_response[3:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            
            parsed_data = json.loads(text_response.strip())
            
            # Ensure amount is a number
            if 'amount' in parsed_data and parsed_data['amount'] is not None:
                if isinstance(parsed_data['amount'], str):
                    # Remove currency symbols and commas
                    cleaned_amount = (parsed_data['amount']
                        .replace(',', '')
                        .replace('$', '')
                        .replace('₹', '')
                        .replace('€', '')
                        .replace('£', '')
                        .strip())
                    try:
                        parsed_data['amount'] = float(cleaned_amount)
                    except ValueError:
                        parsed_data['amount'] = 0.0
            
            # Ensure items have numeric prices
            if 'items' in parsed_data and isinstance(parsed_data['items'], list):
                for item in parsed_data['items']:
                    if 'price' in item and isinstance(item['price'], str):
                        try:
                            item['price'] = float(item['price'].replace(',', '').replace('$', '').replace('₹', '').strip())
                        except ValueError:
                            item['price'] = 0.0
                    
            return parsed_data

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from Gemini: {e}")
            return {"error": "Failed to parse receipt data", "raw_response": text_response if 'text_response' in locals() else None}
        except Exception as e:
            print(f"Error parsing receipt with Gemini: {e}")
            return {"error": f"Failed to parse receipt: {str(e)}"}


# Singleton instance
_ocr_service = None

def get_ocr_service() -> GeminiOCRService:
    """Get or create the singleton OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = GeminiOCRService()
    return _ocr_service
