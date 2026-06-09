[← Back to Overview](Overview.md)

# Assumptions and Constraints

This document outlines the core assumptions and system constraints guiding the development of the TTB Label Compliance prototype.

## Constraints

*   **5-Second Latency:** The system must return compliance results in ~5 seconds per label to maintain workflow efficiency.
*   **Cost Efficiency & Compute Load:** With ~150,000 applications annually, the system sits idle >95% of the time. This constraint drives the decision to use a pay-per-request LLM API (like OpenAI) over hosting costly dedicated open-source GPU instances.
*   **Network & Security Restrictions:** Government networks block outbound traffic, and FedRAMP compliance is required. While the prototype uses public OpenAI endpoints, production systems must utilize internal services like Azure OpenAI. The prototype stores no PII.
*   **User Literacy:** The UI must be dead simple, intuitive, and require no training, accommodating agents of varying tech literacy levels.

## Technical & Product Assumptions

*   **Inputs:** The application document (PDF) and the finalized label artwork (PNG/JPG/PDF) are submitted as separate, single files.
*   **Image Quality:** Photos with glare, curvature, or poor lighting are processed on a best-effort basis.
*   **Scope:** Distilled spirits is the primary rule set implemented.
*   **Government Warning Validation:** Exact text and capitalization are strictly enforced. Visual layout checks (e.g., bolding) are treated as best-effort due to the limitations of text-based LLMs.
*   **Equivalence & Normalization:** For routine fields (Brand Name, ABV), minor typographical differences (case, punctuation, units) are normalized and evaluated for equivalence using the LLM, rather than strict string matching.
*   **Failure Modes:** Low-confidence extraction or missing data must "fail closed," resulting in a "Needs Review" or "Failed" state. It should never automatically pass.
*   **Workflow Integration:** The prototype assumes a standalone, manual upload process. Direct integration into the COLA system (which would allow background asynchronous processing and eliminate the 5-second wait) is considered out of scope but highly recommended for the future.
*   **Bulk Processing:** The 5-second rule applies to single uploads. While the backend supports bulk concurrency, the UI for bulk uploading is omitted in this prototype.
