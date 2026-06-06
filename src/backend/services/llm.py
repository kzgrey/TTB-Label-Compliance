import time
import abc
import base64
import random
from typing import Dict, Any
from openai import OpenAI
from src.backend.config import settings

def timing_decorator(func):
    """Decorator to automatically measure start time, end time, and duration."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        
        # Ensure result is a dict to append metrics
        if not isinstance(result, dict):
            result = {"output": result}
            
        result["start_time"] = start_time
        result["end_time"] = end_time
        result["duration_sec"] = duration
        return result
    return wrapper

class VisionLLMProvider(abc.ABC):
    """
    Generic interface for vision-enabled LLMs.
    """
    
    @abc.abstractmethod
    def execute_prompt(self, prompt: str, image_bytes: bytes) -> Dict[str, Any]:
        """
        Executes a prompt against a vision-enabled LLM with the provided image bytes.
        Must return a dictionary containing the extracted/generated key-values.
        """
        pass

class OpenAIVisionLLM(VisionLLMProvider):
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"

    @timing_decorator
    def execute_prompt(self, prompt: str, image_bytes: bytes) -> Dict[str, Any]:
        """
        Implementation for OpenAI Vision.
        Passes a random seed to prevent caching.
        """
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Random seed to prevent caching
        seed = random.randint(1, 1000000)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1024,
            seed=seed
        )
        
        # Assume structured prompt execution returns parsable output or raw text
        return {
            "text": response.choices[0].message.content,
            "seed_used": seed
        }

# Factory or singleton
def get_llm_provider() -> VisionLLMProvider:
    return OpenAIVisionLLM()
