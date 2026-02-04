import os
from google import genai
from google.genai import types
import json
from typing import Optional, Dict, Any
from PIL import Image
import io

class GeminiOCRService:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found in environment variables.")
        else:
            self.client = genai.Client(api_key=api_key)

    def parse_receipt(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Parses a receipt image using Gemini and returns structured data.
        Automatically falls back to gemini-1.5-flash if 2.0-flash quota is exceeded.
        """
        if not hasattr(self, 'client'):
             return {"error": "Gemini API key not configured"}

        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            prompt = """
            Analyze this receipt image and extract the following information in JSON format:
            - amount: The total amount (numeric only, no currency symbols).
            - currency: The currency code (e.g., USD, INR).
            - description: A brief description of the purchase (e.g., "Restaurant bill", "Grocery store").
            - date: The date of purchase in YYYY-MM-DD format.
            - items: A list of items purchased, with 'name' and 'price'.
            
            Return ONLY the JSON object, no markdown formatting.
            """

            # Try gemini-2.0-flash first, fallback to 1.5-flash if quota exceeded
            try:
                response = self.client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=[prompt, image]
                )
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    print("Gemini 2.0 Flash quota exceeded, falling back to 2.5 Flash...")
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[prompt, image]
                    )
                else:
                    raise
            
            # Clean up response text if it contains markdown code blocks
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            
            parsed_data = json.loads(text_response.strip())
            
            # Ensure amount is a number
            if 'amount' in parsed_data:
                if isinstance(parsed_data['amount'], str):
                    # Remove currency symbols and commas
                    cleaned_amount = parsed_data['amount'].replace(',', '').replace('$', '').replace('₹', '').strip()
                    parsed_data['amount'] = float(cleaned_amount)
                    
            return parsed_data

        except Exception as e:
            print(f"Error parsing receipt with Gemini: {e}")
            return {"error": f"Failed to parse receipt: {str(e)}"}
