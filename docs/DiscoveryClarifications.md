[← Back to Overview](Overview.md)

# Discovery & Pre-Implementation Clarifications

Before writing code for this prototype, a product discovery and clarification phase was conducted to ensure alignment with stakeholder needs and to evaluate alternative engineering approaches. This document serves as a record of those initial considerations and the email sent to stakeholders prior to implementation.

## 1. Evaluating Alternative Approaches (Build vs. Salvage)
In a real-world enterprise scenario, assuming a complete rewrite is necessary is an anti-pattern. Given that a prior vendor pilot existed, the first step would be to perform a root-cause analysis on why it failed:
- Was it OCR/model quality?
- Deployment architecture or network restrictions?
- A synchronous workflow bottleneck?
- Manual ingestion delays?

If the previous system was functionally sound but poorly integrated, the optimal engineering decision might have been to performance-profile and adapt the existing system rather than replacing it entirely. Furthermore, surveying other government organizations could reveal whether adapting the existing tool could automate adjacent workflows.

## 2. Workflow Integration: Synchronous vs. Asynchronous Ingestion
The take-home project mandates a standalone tool with a 5-second SLA for manual uploads. However, from an engineering leadership perspective, a more robust solution for the actual COLA system was proposed upfront:
- **Automated Ingestion:** Instead of agents manually uploading files, the new system should automatically ingest applications directly from COLA as they arrive.
- **Hiding Latency:** If ingestion is automated and handled asynchronously in the background, the 30-40 second processing latency of the prior vendor pilot becomes irrelevant. The agent simply opens the application, and the pre-computed compliance report is already waiting. From the user's perspective, the processing time is zero.

## 3. Scope & Assumptions Establishment
Because the COLA integration was out of scope for the prototype, it was necessary to explicitly define the boundaries of the take-home exercise. A list of 13 clarifying questions and assumptions was sent to the stakeholders, establishing the rules of engagement before development began. These bounded the problem space and directly informed the architecture:
- Treating inputs as finalized artwork (best-effort for photos/glare).
- Focusing initially on Distilled Spirits.
- Permitting backend-mediated third-party APIs (like OpenAI) provided keys are secured.
- Normalizing routine fields for equivalence while strictly enforcing the text of the Government Warning.
- Ensuring the system fails closed (Needs Review) on low-confidence extractions.

By addressing these architectural and product questions upfront, the prototype was built on a foundation of explicit, shared understanding rather than unvalidated assumptions.

## 4. Research & Benchmarking (OCR and LLMs)
To determine the feasibility of meeting the strict 5-second SLA while balancing cost and accuracy, various OCR and LLM combinations were evaluated during the discovery phase prior to implementation.

**OCR Systems Evaluated:**
- **Tesseract (Local):** Extremely fast (<1 second) and cost-free. While it struggles with curved surfaces or heavy glare on physical bottles, it performs well on flat digital artwork.
- **Cloud OCR (AWS Textract / Google Cloud Vision):** High accuracy, but introduces network latency (1-3 seconds) and requires strict outbound traffic approvals in a government environment.
- **Vision LLMs (GPT-4o / Gemini 1.5 Pro):** Capable of performing both OCR and field extraction in a single step. However, processing high-resolution images can push response times to 6-12 seconds, posing a high risk to the 5-second SLA.

**LLM Systems Evaluated (For Extraction & Equivalence):**
- **OpenAI (GPT-4o-mini) & Google Gemini (1.5 Flash):** Both provide extremely low latency (1-3 seconds for text payloads) and high accuracy for JSON extraction and semantic equivalence checking. They easily fit within the 5-second SLA when fed pre-extracted text.
- **Local Open-Source (e.g., Llama 3 8B):** While satisfying all network/security constraints, maintaining a dedicated GPU cluster to serve requests with sub-5-second latency would be prohibitively expensive given the 95% idle time calculation.

**Conclusion:** A hybrid approach—using a fast local OCR pass (like Tesseract) combined with a lightweight, low-latency LLM API (like GPT-4o-mini or Gemini Flash) for data extraction and validation—was deemed the most feasible path. This ensures the system reliably hits the 5-second SLA while keeping infrastructure costs minimal.
