[← Back to Overview](Overview.md)

# Extensibility Guide: Adding New Beverage Rules

The current prototype implements the rule set and prompts specifically for **Distilled Spirits**. However, the system's architecture follows the Open/Closed principle, allowing new beverage types (e.g., Wine, Malt Beverages/Beer) to be added without modifying the core extraction engine.

## How to Add a New Beverage Type

1. **Create the Pydantic Data Model:**
   In `src/backend/extraction/`, create a new Pydantic schema (e.g., `wine_label_construction.py`) that defines the expected fields for the new beverage class. This schema enforces structured JSON output from the LLM.

2. **Define the LLM Prompts:**
   In `src/backend/prompts/`, create a new prompt template detailing the specific TTB compliance rules for that beverage type (e.g., specific ABV tolerance and vintage rules for wine).

3. **Implement the Validation Rules Engine:**
   In `src/backend/validators/`, create a rule dictionary mapping the extracted fields to pass/fail logic. Ensure the deterministic logic aligns with the specific CFR regulations for that beverage class.

4. **Register the Beverage Class:**
   Update the main job orchestrator (`src/backend/jobs/analyze_label.py`) to conditionally route the extraction and validation logic based on the `beverage_type` specified in the incoming application document.
