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

def process_image_with_llm(file_bytes: bytes) -> dict:
    from src.backend.services.llm import get_llm_provider
    start_time = time.time()

    provider = get_llm_provider()
    prompt = "Transcribe all text visible in this image exactly as written. Output only the transcribed text, preserving newlines."
    
    # Invoke LLM prompt
    llm_result = provider.execute_prompt(prompt, file_bytes)

    end_time = time.time()
    duration_sec = end_time - start_time
    
    text = llm_result.get("text", "")
    
    return {
        "text": text.strip(),
        "duration_sec": duration_sec
    }