import pytest
from unittest.mock import patch, MagicMock, ANY
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

def test_analyze_label_job_mocked():
    with patch('src.backend.jobs.analyze_label.download_job_input') as mock_download, \
         patch('src.backend.jobs.analyze_label.process_image_with_tesseract') as mock_ocr, \
         patch('src.backend.jobs.analyze_label.get_llm_provider') as mock_llm_provider, \
         patch('src.backend.jobs.base.SessionLocal') as mock_session_local:
         
        mock_download.return_value = b"fake_image_bytes"
        mock_ocr.return_value = {"text": "OCR Mock Output", "duration_sec": 1.2}
        
        mock_provider = MagicMock()
        mock_provider.execute_prompt.return_value = {"text": "LLM Mock Output", "duration_sec": 2.3}
        mock_llm_provider.return_value = mock_provider
        
        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_job.status = "pending"
        mock_db.query().filter().first.return_value = mock_job
        mock_session_local.return_value = mock_db
        
        from src.backend.jobs.analyze_label import AnalyzeLabelJob
        
        with patch('src.backend.jobs.base.BaseJob.upload_file') as mock_upload_file:
            job = AnalyzeLabelJob("test-job-id")
            result = job.execute(file_key="test-key", prompt="test-prompt")
            
            assert result["ocr_output"] == "OCR Mock Output"
            assert result["llm_output"] == "LLM Mock Output"
            assert result["ocr_duration_sec"] == 1.2
            assert result["llm_duration_sec"] == 2.3
            assert "total_duration_sec" in result
            
            # Verify S3 upload calls
            mock_upload_file.assert_any_call("output.json", ANY)
            mock_upload_file.assert_any_call("log.txt", ANY)

