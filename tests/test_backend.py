import pytest
from unittest.mock import patch, MagicMock
from src.backend.services.llm import OpenAIVisionLLM
from src.backend.services.ocr import process_image_with_tesseract

def test_ocr_service_mocked():
    with patch('src.backend.services.ocr.pytesseract.image_to_string') as mock_tesseract, \
         patch('src.backend.services.ocr.Image.open') as mock_image:
        mock_tesseract.return_value = "Mocked OCR Text"
        
        # Call the service
        result = process_image_with_tesseract(b"fake_image_bytes")
        
        assert result["text"] == "Mocked OCR Text"
        assert "duration_sec" in result

def test_llm_service_mocked():
    with patch('src.backend.services.llm.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"key": "value"}'))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = OpenAIVisionLLM()
        result = provider.execute_prompt("Analyze this", b"fake_image_bytes")
        
        assert result["text"] == '{"key": "value"}'
        assert "seed_used" in result
        assert "start_time" in result
        assert "end_time" in result
        assert "duration_sec" in result
