[← Back to Overview](Overview.md)

# Reviewer's Guide & Test Cases

If you are evaluating this prototype, this guide will help you understand the expected behavior and how to effectively test the system's capabilities.

## Evaluating the System

When submitting an application, the system evaluates the label across multiple fields. For each field, the system will return one of three states:
- **Passed (Green):** The LLM and deterministic rules agreed that the label text is functionally equivalent to the application document. Minor case/punctuation differences are normalized successfully.
- **Failed (Red):** A hard mismatch was found (e.g., ABV is 40% on the app, but 45% on the label).
- **Needs Review (Yellow):** The text could not be found, or the OCR extraction confidence was too low. The system "fails closed" to ensure an agent manually verifies the data.

## Recommended Test Scenarios

To fully test the system, we recommend generating or sourcing test labels and applications that fit the following profiles:

1. **The "Happy Path" (Clean Pass)**
   - **Input:** Clean, flat digital label artwork. The application JSON/PDF matches the label exactly.
   - **Expected Output:** All fields return green. Processing completes in < 5 seconds.

2. **The "Nuanced Match" (Semantic Equivalence)**
   - **Input:** An application listing the brand as `STONE'S THROW`, but the label shows `Stone's Throw`. Net contents listed as `750ml` vs `750 mL`.
   - **Expected Output:** System successfully normalizes the strings and passes the fields, proving the LLM's superiority over rigid Regex matching.

3. **The "Hard Failure" (Mismatch)**
   - **Input:** An application listing `Straight Bourbon Whiskey`, but the label says `Rye Whiskey`.
   - **Expected Output:** The Class/Type field explicitly fails.

4. **The "Imperfect Input" (Needs Review)**
   - **Input:** A heavily distorted photograph of a bottle with severe glare obscuring the ABV.
   - **Expected Output:** The OCR engine fails to extract the ABV text reliably. The system flags the ABV field as `Needs Review`, requiring human intervention.
