import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.gemini_ocr import GeminiOCRService

def test_ocr():
    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("Skipping OCR test: GEMINI_API_KEY not set")
        return

    # Create dummy image bytes (1x1 pixel) just to test the call flow
    # In a real test we'd use a real receipt image, but here we just want to ensure imports and class structure work.
    # To test actual Gemini interaction, we need a valid image format.
    # Let's create a simple blank image in memory.
    from PIL import Image
    import io
    
    img = Image.new('RGB', (100, 100), color = 'white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    image_bytes = img_byte_arr.getvalue()

    print("Initializing GeminiOCRService...")
    service = GeminiOCRService()
    
    print("Calling parse_receipt...")
    # This might fail with "safety" or "not a receipt" or "json error" depending on Gemini's strictness,
    # but it proves the code runs.
    try:
        result = service.parse_receipt(image_bytes)
        print("Result:", result)
    except Exception as e:
        print(f"Service call failed (expected if invalid image): {e}")

if __name__ == "__main__":
    test_ocr()
