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
        
        self.logger.info("Starting concurrent extraction pipeline")
        start_time = time.time()

        # 1. Run OCR synchronously so it doesn't compete for resources
        if use_llm_ocr:
            from src.backend.services.ocr import process_image_with_llm
            ocr_result = process_image_with_llm(self.file_bytes)
        else:
            ocr_result = process_image_with_tesseract(self.file_bytes)
            
        ocr_text = ocr_result.get("text", "")
        ocr_duration = ocr_result.get("duration_sec", 0.0)

        # 2. Extract Application values (sync) because ABV comparison requires it
        app_result = self.extract_application(self.application_detail_text)
        app_abv = None
        if app_result.get("data"):
            app_abv = app_result["data"].ABV

        # 3. Run LLM Tasks concurrently
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_norm = executor.submit(self.run_normalization_llm, ocr_text)
            future_warn = executor.submit(self.run_warning_llm, ocr_text)
            future_abv = executor.submit(self.run_abv_llm, ocr_text, app_abv)
            
            norm_result = future_norm.result()
            warn_result = future_warn.result()
            abv_result = future_abv.result()

        llm_json = norm_result.get("json", {})
        label_dict = llm_json.get("Label", {})
        
        warn_json = warn_result.get("json", {})
        label_dict["IsGovernmentWarningHeaderCorrectLLM"] = warn_json.get("IsGovernmentWarningHeaderCorrectLLM")
        label_dict["IsGovernmentWarningTextCorrectLLM"] = warn_json.get("IsGovernmentWarningTextCorrectLLM")

        abv_json = abv_result.get("json", {})
        label_dict["IsABVCorrectLLM"] = abv_json.get("IsABVCorrectLLM")

        from src.backend.extraction.unified_schema import LabelData
        try:
            data = LabelData(**label_dict)
        except Exception as e:
            self.logger.error(f"Failed to parse LabelData: {e}")
            data = None

        total_duration = time.time() - start_time
        self.logger.info(f"Concurrent processing completed in {total_duration:.2f}s")
        
        from src.backend.validators.distilled_spirits_label_rule_dicts import evaluate_rules
        
        try:
            rule_dicts = evaluate_rules(data, app_result["data"])
            rules_passed = rule_dicts.get("passed", {})
            rules_failed = rule_dicts.get("failed", {})
            rules_unknown = rule_dicts.get("unknown", {})
        except Exception as e:
            self.logger.error(f"Failed to evaluate rules: {e}")
            rules_passed = {}
            rules_failed = {}
            rules_unknown = {}

        final_output = {
            "ocr_output": ocr_text,
            "ocr_duration_sec": ocr_duration,
            "llm_output": norm_result.get("text", ""),
            "llm_extracted_json": llm_json,
            "normalization_llm_duration_sec": norm_result.get("duration_sec", 0.0),
            "warning_llm_duration_sec": warn_result.get("duration_sec", 0.0),
            "abv_llm_duration_sec": abv_result.get("duration_sec", 0.0),
            "application_llm_duration_sec": app_result.get("duration_sec", 0.0),
            "total_duration_sec": total_duration,
            "rules_passed": rules_passed,
            "rules_failed": rules_failed,
            "rules_unknown": rules_unknown,
            "application_data": app_result["data"].model_dump() if app_result.get("data") else None,
        }

        # Write final outputs to S3
        outputs_key = f"{self.job_id}/output.json"
            
        return final_output

    def run_normalization_llm(self, ocr_text: str) -> dict:
        from src.backend.prompts.gpt_mini_prompts import NORMALIZE_TEXTBLOCKS_PROMPT2
        combined_prompt = f"User Instructions:\n{NORMALIZE_TEXTBLOCKS_PROMPT2}\n\nExtracted OCR Text:\n{ocr_text}"
        provider = get_llm_provider()
        return provider.execute_json_prompt(combined_prompt)

    def run_warning_llm(self, ocr_text: str) -> dict:
        from src.backend.prompts.gpt_mini_prompts import GOVERNMENT_WARNING_CHECK_PROMPT
        combined_prompt = f"User Instructions:\n{GOVERNMENT_WARNING_CHECK_PROMPT}\n\nExtracted OCR Text:\n{ocr_text}"
        provider = get_llm_provider(model_name="gpt-5.4-mini")
        return provider.execute_json_prompt(combined_prompt)

    def run_abv_llm(self, ocr_text: str, app_abv: str) -> dict:
        if not app_abv:
            return {"json": {"IsABVCorrectLLM": None}, "duration_sec": 0.0}
            
        from src.backend.prompts.gpt_mini_prompts import ABV_EQUIVALENCE_PROMPT
        combined_prompt = f"User Instructions:\n{ABV_EQUIVALENCE_PROMPT}\n\nExtracted Application ABV Value:\n{app_abv}\n\nExtracted OCR Text:\n{ocr_text}"
        provider = get_llm_provider(model_name="gpt-5.4-mini")
        return provider.execute_json_prompt(combined_prompt)

    def extract_application(self, text: str) -> dict:
        self.logger.info("Starting Application LLM extraction")
        if not text or not text.strip():
            return {"data": None, "duration_sec": 0.0}
            
        from src.backend.prompts.gpt_mini_prompts import EXTRACT_APPLICATION_PROMPT
        combined_prompt = f"{EXTRACT_APPLICATION_PROMPT}\n\nPasted Text:\n{text}"
        
        provider = get_llm_provider(model_name="gpt-5.4-mini")
        llm_result = provider.execute_json_prompt(combined_prompt)
        
        from src.backend.extraction.unified_schema import LabelData
        try:
            data = LabelData(**llm_result.get("json", {}))
        except Exception as e:
            self.logger.error(f"Failed to parse Application LabelData: {e}")
            data = None
            
        return {
            "data": data,
            "duration_sec": llm_result.get("duration_sec", 0.0)
        }

    def cleanup(self):
        self.logger.info("Cleaning up resources.")
        self.file_bytes = None


