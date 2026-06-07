# Distilled spirits label construction layer

This layer converts raw text inputs into the dataclasses used by the label validator:

```python
DistilledSpiritsLabelReviewInput(
    application=DistilledSpiritsApplication(...),
    label=DistilledSpiritsLabelExtraction(...),
)
```

## Files

- `distilled_spirits_label_dataclasses.py` — the review/application/label dataclass model.
- `distilled_spirits_label_construction.py` — deterministic + LLM-assisted construction logic.
- `example_construct_review_input.py` — runnable example using the SAO PAULO application paste and OCR-like blocks.

## Basic use

```python
from distilled_spirits_label_construction import construct_review_input

result = construct_review_input(
    application_detail_text=application_detail_text,
    ocr_text_blocks=[
        "SAO PAULO GOLD RUM",
        "PRODUCE OF BRAZIL",
        "40% ALC BY VOL (80 PROOF)",
        "750 mL",
        "IMPORTED BY MONTEBELLO BRANDS, INC. BALTIMORE, MD",
        "GOVERNMENT WARNING: (1) According to the Surgeon General, ...",
    ],
)

review_input = result.review_input
```

## LLM use

Pass any object implementing this protocol:

```python
class JsonLlm:
    def complete_json(self, *, system_prompt: str, user_prompt: str, json_schema: dict) -> dict:
        ...
```

The constructor always runs deterministic parsing first, sends the raw inputs plus deterministic seed to the LLM, then re-applies deterministic post-processing. This makes the LLM useful for ambiguous field assignment while keeping exact text checks, numeric extraction, and simple comparisons stable.

## What the deterministic layer resolves

- Application paste fields: TTB ID, status, serial, vendor code, class/type code, origin code, brand name, formula, approval date, principal-place-of-business permit block, and contact block.
- Label text fields: brand match, class/type match, ABV/proof, net contents, responsible-party phrase, country of origin, commodity statement, age statement, state-of-distillation text, government-warning text, and common conditional disclosures.
- Precomputed checks: a bootstrap set keyed by rule IDs such as `DS-LABEL-001.brand_name_present`, `DS-LABEL-011.class_type_matches_application`, `DS-LABEL-080.alcohol_content_present`, `DS-LABEL-060.country_of_origin_present`, and `DS-LABEL-191.government_warning_exact_text`.

## Intentional limitations

- Text size, color/background contrast, and label positioning are ignored.
- Text-only OCR cannot prove boldness or continuous-paragraph formatting. The government-warning exact text and all-caps header checks are computed, but full warning compliance remains `UNKNOWN` unless richer OCR/style metadata or a visual analysis layer supplies those facts.
- The copied application detail often omits ABV and total bottle capacity. When absent, application-vs-label ABV/net-content match checks stay unknown rather than guessed.
