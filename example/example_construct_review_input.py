"""Minimal example for distilled_spirits_label_construction.py.

Run from the same directory as:
    python example_construct_review_input.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/backend/extraction')))

from distilled_spirits_label_construction import construct_review_input, dataclass_to_dict, dump_review_input_json

APPLICATION_DETAIL_TEXT = """
TTB ID: Open help for the TTB ID field in a new window 13221001000316
Status: Open help for the Status field in a new window   SURRENDERED
Vendor Code: Open help for the Vendor Code field in a new window   12393
Serial #: Open help for the Serial Number field in a new window   130002
Class/Type Code: Open help for the Class/Type Code field in a new window OTHER RUM GOLD USB
Origin Code: Open help for the Origin Code field in a new window   BRAZIL
Brand Name: Open help for the Brand Name field in a new window   SAO PAULO
Type of Application: Open help for the Type of Application field in a new window   LABEL APPROVAL
Formula : Open help for the Formula field in a new window   1183981
Approval Date:   10/24/2013
Plant Registry/Basic Permit/Brewers No (Principal Place of Business): Open help for the Plant Registry/Basic Permit/Brewers Number field in a new window
DSP-MD-18
MONTEBELLO BRANDS, INC.
1919 WILLOW SPRING RD
BALTIMORE, MD 21222
Contact Information:
NANCY   HOGAN
Phone Number:  (410) 282-8800
"""

OCR_BLOCKS = [
    "SAO PAULO GOLD RUM",
    "PRODUCE OF BRAZIL",
    "40% ALC BY VOL (80 PROOF)",
    "750 mL",
    "IMPORTED BY MONTEBELLO BRANDS, INC. BALTIMORE, MD",
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.",
]

# Deterministic-only mode:
result = construct_review_input(
    application_detail_text=APPLICATION_DETAIL_TEXT,
    ocr_text_blocks=OCR_BLOCKS,
    source_filename="example-label.jpg",
)

# With an LLM, pass an object that implements JsonLlm.complete_json(...).
# result = construct_review_input(application_detail_text=APPLICATION_DETAIL_TEXT, ocr_text_blocks=OCR_BLOCKS, llm=my_llm)

review = result.review_input
import json
print("Application:")
print(json.dumps(dataclass_to_dict(review.application, include_none=False), indent=2))
print("\nLabel:")
print(json.dumps(dataclass_to_dict(review.label, include_none=False), indent=2))
print("\nPrecomputed checks:")
print(json.dumps(dataclass_to_dict(review.checks, include_none=False), indent=2))

dump_review_input_json(review, "example_review_input.json")
print("\nWrote example_review_input.json")
