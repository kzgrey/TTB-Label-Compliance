import time
import io
import pytesseract
from PIL import Image

def process_image_with_tesseract(file_bytes: bytes) -> dict:
    """
    Runs Tesseract OCR on the image bytes.
    Returns a dictionary with 'text' and 'duration_sec'.
    """
    start_time = time.time()
    
    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image)
    
    end_time = time.time()
    duration_sec = end_time - start_time
    
    return {
        "text": text.strip(),
        "duration_sec": duration_sec
    }
