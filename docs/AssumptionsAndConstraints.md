[← Back to Overview](Overview.md)

# Assumptions and Constraints

This document outlines the core assumptions and system constraints guiding the development of the TTB Label Compliance prototype.

## Constraints

*   **5-Second Latency:** The system must return compliance results in ~5 seconds per label to maintain workflow efficiency.
*   **Cost Efficiency & Compute Load:** With ~150,000 applications annually, the system sits idle >95% of the time. This constraint drives the decision to use a pay-per-request external LLM API over hosting costly dedicated open-source GPU instances. The system is inherently optimized for bursty workload patterns rather than constant high utilization.
*   **Cloud Portability:** The deployment model is container-based. While AWS CDK scripts exist, the architecture is fundamentally cloud-portable across AWS, Azure, or Google Cloud.
*   **Network & Security Restrictions:** Government networks block outbound traffic, and FedRAMP compliance is required. While the prototype uses public OpenAI endpoints, production systems must utilize internal services like Azure OpenAI. The prototype stores no PII.
*   **User Literacy:** The UI must be dead simple, intuitive, and require no training, accommodating agents of varying tech literacy levels.

## Technical & Product Assumptions

*   **Inputs:** The application document (PDF) and the finalized label artwork (PNG/JPG/PDF) are submitted as separate, single files.
*   **Image Quality & Remediation:** Photographed bottle labels (involving glare, poor lighting, perspective distortion, occlusion) are processed on a **best-effort** basis. To fully support real-world photos, advanced image remediations would be required, including perspective correction (deskewing), glare removal, label segmentation, and bottle detection.
*   **Scope of Compliance Rules:** Full coverage of every beverage-specific TTB rule is outside scope. The prototype targets representative high-value checks (initially focusing on Distilled Spirits).
*   **Government Warning Validation:** Exact text and capitalization are strictly enforced. Visual-format validation (font size, bolding, prominence, relative placement, or text positioning) is treated as a **best-effort** check due to the limitations of text-based LLMs. Full, reliable visual TTB rule validation would require enhanced OCR with layout metadata (bounding boxes) or a dedicated computer-vision model.
*   **Equivalence & Normalization:** The LLM is utilized for extraction, normalization, and ambiguity handling of fields (Brand Name, ABV). However, deterministic rules remain the preferred method for exact comparisons.
*   **Failure Modes:** The system is not a final regulatory decision-maker. Ambiguous or low-confidence results should be surfaced for human review. It must "fail closed" into a "Needs Review" state and never automatically pass.
*   **Workflow Integration:** The prototype assumes a standalone, manual upload process. Direct COLA integration, production authorization workflows, document-retention policy enforcement, and agency identity integration are outside the prototype scope.
*   **Asynchronous Workers:** The 5-second rule applies to single uploads. The Celery workers are primarily utilized for batch processing, retries, and isolation of longer-running work.
