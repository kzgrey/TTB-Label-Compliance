import time
from src.backend.jobs.base import BaseJob
from src.backend.services.s3 import download_job_input
from src.backend.services.ocr import process_image_with_tesseract
from src.backend.services.llm import get_llm_provider
from src.backend.prompts.gpt_mini_prompts import NORMALIZE_TEXTBLOCKS_PROMPT2

class AnalyzeLabelJob(BaseJob):
    """
    Analyzes a TTB label application by performing OCR on the input image and running LLM checks.
    """
    def initialize(self, file_key: str, *args, **kwargs):
        self.logger.info(f"Downloading input file from S3: {file_key}")
        self.file_bytes = download_job_input(file_key)

    def run(self, file_key: str, prompt: str = "", use_llm_ocr: bool = False, *args, **kwargs):
        self.application_detail_text = prompt
        
        self.logger.info("Starting concurrent extraction for OCR/Label and Application")
        start_time = time.time()

        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_label = executor.submit(self.extract_label, use_llm_ocr, self.file_bytes)
            future_app = executor.submit(self.extract_application, self.application_detail_text)
            
            label_result = future_label.result()
            app_result = future_app.result()

        total_duration = time.time() - start_time
        self.logger.info(f"Concurrent processing completed in {total_duration:.2f}s")
        
        from src.backend.validators.distilled_spirits_label_rule_dicts import evaluate_rules
        
        try:
            rule_dicts = evaluate_rules(label_result["data"], app_result["data"])
            rules_passed = rule_dicts.get("passed", {})
            rules_failed = rule_dicts.get("failed", {})
            rules_unknown = rule_dicts.get("unknown", {})
        except Exception as e:
            self.logger.error(f"Failed to evaluate rules: {e}")
            rules_passed = {}
            rules_failed = {}
            rules_unknown = {}

        final_output = {
            "ocr_output": label_result["ocr_text"],
            "ocr_duration_sec": label_result["ocr_duration"],
            "llm_output": label_result["llm_text"],
            "llm_extracted_json": label_result["llm_json"],
            "llm_duration_sec": label_result["llm_duration"],
            "total_duration_sec": total_duration,
            "rules_passed": rules_passed,
            "rules_failed": rules_failed,
            "rules_unknown": rules_unknown,
            "application_data": app_result["data"].model_dump() if app_result.get("data") else None,
        }

        # Write final outputs to S3
        outputs_key = f"{self.job_id}/output.json"
            
        return final_output

    def extract_label(self, use_llm_ocr: bool, file_bytes: bytes) -> dict:
        self.logger.info(f"Starting {'LLM OCR' if use_llm_ocr else 'Tesseract OCR'} processing")
        if use_llm_ocr:
            from src.backend.services.ocr import process_image_with_llm
            ocr_result = process_image_with_llm(file_bytes)
        else:
            ocr_result = process_image_with_tesseract(file_bytes)
            
        ocr_text = ocr_result.get("text", "")
        ocr_duration = ocr_result.get("duration_sec", 0.0)
        
        from src.backend.prompts.gpt_mini_prompts import NORMALIZE_TEXTBLOCKS_PROMPT2
        combined_prompt = f"User Instructions:\n{NORMALIZE_TEXTBLOCKS_PROMPT2}\n\nExtracted OCR Text:\n{ocr_text}"
        
        provider = get_llm_provider()
        llm_result = provider.execute_json_prompt(combined_prompt, file_bytes)
        
        llm_json = llm_result.get("json", {})
        label_dict = llm_json.get("Label", {})
        
        from src.backend.extraction.unified_schema import LabelData
        try:
            data = LabelData(**label_dict)
        except Exception as e:
            self.logger.error(f"Failed to parse LabelData: {e}")
            data = None
            
        return {
            "ocr_text": ocr_text,
            "ocr_duration": ocr_duration,
            "llm_text": llm_result.get("text", ""),
            "llm_json": llm_json,
            "llm_duration": llm_result.get("duration_sec", 0.0),
            "data": data
        }

    def extract_application(self, text: str) -> dict:
        self.logger.info("Starting Application LLM extraction")
        if not text or not text.strip():
            return {"data": None}
            
        from src.backend.prompts.gpt_mini_prompts import EXTRACT_APPLICATION_PROMPT
        combined_prompt = f"{EXTRACT_APPLICATION_PROMPT}\n\nPasted Text:\n{text}"
        
        provider = get_llm_provider()
        llm_result = provider.execute_json_prompt(combined_prompt)
        
        from src.backend.extraction.unified_schema import LabelData
        try:
            data = LabelData(**llm_result.get("json", {}))
        except Exception as e:
            self.logger.error(f"Failed to parse Application LabelData: {e}")
            data = None
            
        return {
            "data": data
        }

    def cleanup(self):
        self.logger.info("Cleaning up resources.")
        self.file_bytes = None


