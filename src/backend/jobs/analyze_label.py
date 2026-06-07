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
        self.prompt = NORMALIZE_TEXTBLOCKS_PROMPT2

        self.logger.info(f"Starting {'LLM OCR' if use_llm_ocr else 'Tesseract OCR'} processing")
        start_time = time.time()
        
        # Execute OCR synchronously within the worker process
        if use_llm_ocr:
            from src.backend.services.ocr import process_image_with_llm
            ocr_result = process_image_with_llm(self.file_bytes)
        else:
            ocr_result = process_image_with_tesseract(self.file_bytes)
            
        ocr_text = ocr_result.get("text", "")
        ocr_duration = ocr_result.get("duration_sec", 0.0)
        self.logger.info(f"OCR Duration: {ocr_duration}s")
        self.logger.info(f"OCR Extracted Text:\n{ocr_text}")

        # Next, make an LLM call using that text and a prompt.
        combined_prompt = f"User Instructions:\n{self.prompt}\n\nExtracted OCR Text:\n{ocr_text}"
        self.logger.info("Executing LLM call")
        provider = get_llm_provider()
        llm_result = provider.execute_prompt(combined_prompt, self.file_bytes)
        
        llm_text = llm_result.get("text", "")
        llm_duration = llm_result.get("duration_sec", 0.0)
        self.logger.info(f"LLM Duration: {llm_duration}s")
        self.logger.info(f"LLM Response:\n{llm_text}")
            
        total_duration = time.time() - start_time
        self.logger.info(f"OCR & LLM Processing completed in {total_duration:.2f}s")
        
        # Format the output as expected by the frontend
        llm_duration = llm_result.get("duration_sec", 0.0)
        self.logger.info(f"LLM Response:\n{llm_text}")

        import json
        from src.backend.extraction.distilled_spirits_label_construction import construct_review_input, dataclass_to_dict
        from src.backend.validators.distilled_spirits_label_rule_dicts import build_rule_result_dicts

        try:
            clean_json = llm_text.replace("```json", "").replace("```", "").strip()
            llm_json = json.loads(clean_json)
            
            label_dict = llm_json.get("Label", {})
            normalized_blocks = [v for v in label_dict.values() if isinstance(v, str)]
            
            result = construct_review_input(
                application_detail_text=self.application_detail_text,
                ocr_text_blocks=normalized_blocks,
            )
            rule_dicts = build_rule_result_dicts(result.review_input)
            
            rules_passed = {k: dataclass_to_dict(v) for k, v in rule_dicts.rule_passes.items()}
            rules_failed = {k: dataclass_to_dict(v) for k, v in rule_dicts.rule_fails.items()}
            rules_unknown = {k: dataclass_to_dict(v) for k, v in rule_dicts.rule_unknown.items()}
        except Exception as e:
            self.logger.error(f"Failed to parse LLM JSON or run rules: {e}")
            llm_json = {"error": str(e)}
            rules_passed = {}
            rules_failed = {}
            rules_unknown = {}

        final_output = {
            "ocr_output": ocr_text,
            "ocr_duration_sec": ocr_duration,
            "llm_output": llm_text,
            "llm_extracted_json": llm_json,
            "llm_duration_sec": llm_duration,
            "total_duration_sec": total_duration,
            "rules_passed": rules_passed,
            "rules_failed": rules_failed,
            "rules_unknown": rules_unknown,
        }

        # Write final outputs to S3
        outputs_key = f"{self.job_id}/output.json"
            
        return final_output

    def cleanup(self):
        self.logger.info("Cleaning up resources.")
        self.file_bytes = None


