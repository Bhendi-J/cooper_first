import os
import io
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Load environment variables
load_dotenv()

# Set dummy API key if not present for testing import/initialization logic
# (The actual API call will fail if the key is invalid, but we want to test the flow)
if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    print("WARNING: GEMINI_API_KEY not found in environment variables.")

try:
    from app.services.gemini_ocr import get_ocr_service
except ImportError:
    # Handle case where we run this script from backend/ directly
    import sys
    sys.path.append(os.getcwd())
    from app.services.gemini_ocr import get_ocr_service

def create_dummy_receipt():
    """Create a simple dummy receipt image."""
    # Create white image
    img = Image.new('RGB', (400, 600), color='white')
    d = ImageDraw.Draw(img)
    
    # Add some text
    # Note: Default font is used, which is small but should be readable by Gemini
    d.text((100, 50), "STORE NAME", fill=(0, 0, 0))
    d.text((50, 100), "Item 1       $10.00", fill=(0, 0, 0))
    d.text((50, 130), "Item 2       $20.50", fill=(0, 0, 0))
    d.text((50, 160), "----------------", fill=(0, 0, 0))
    d.text((50, 190), "Total        $30.50", fill=(0, 0, 0))
    d.text((100, 250), "Thank you!", fill=(0, 0, 0))
    d.text((100, 280), "2024-02-05", fill=(0, 0, 0))
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def test_ocr():
    print("Initialising OCR Service...")
    service = get_ocr_service()
    
    if not service.is_available():
        print("ERROR: OCR Service is not available.")
        print("Check if 'google-genai' and 'Pillow' are installed and GEMINI_API_KEY is set.")
        return

    print("Creating dummy receipt image...")
    image_bytes = create_dummy_receipt()
    
    print("Sending image to Gemini for analysis (using 'gemini-2.0-flash' or fallback)...")
    try:
        # Debug: Check SDK version and available models
        try:
            import google.genai as genai
            print(f"SDK Version: {getattr(genai, '__version__', 'unknown')}")
        except:
            pass
            
        result = service.parse_receipt(image_bytes)
        
        print("\n--- OCR RESULT ---")
        print(result)
        
        if "error" in result:
            print(f"\nExample Failed: {result['error']}")
            
            # Try to list models to help debugging
            if service.client:
                print("\nAttempting to list available models...")
                try:
                    for m in service.client.models.list(config={"page_size": 10}):
                        print(f" - {m.name}")
                except Exception as list_err:
                    print(f"Could not list models: {list_err}")
                
        else:
            print("\nSUCCESS! Extracted data:")
            print(f"Merchant: {result.get('merchant')}")
            print(f"Total: {result.get('amount')} {result.get('currency')}")
            print(f"Date: {result.get('date')}")
            print(f"Items: {len(result.get('items', []))}")
            
    except Exception as e:
        print(f"\nException during testing: {e}")

if __name__ == "__main__":
    test_ocr()
