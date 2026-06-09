# TTB Label Compliance System - Next Steps Roadmap

This document outlines the strategic roadmap for evolving the TTB Label Compliance prototype into a production-ready system. It incorporates insights from stakeholder Agent Interviews, project assumptions, discovery notes, and the existing documentation repository.

## 1. UX Research via Surveys and Experiments
**Goal:** Ensure the application meets the diverse technical literacy levels of compliance agents.
*   **Justification:** The TTB workforce has a wide range of tech comfort levels (e.g., paper-based workflows vs. digital natives). As learned from the failed vendor pilot, poor usability directly leads to system abandonment, regardless of technical accuracy.
*   **Action Items:**
    *   Conduct structured user interviews and A/B testing with compliance agents (from highly technical to paper-based workflows).
    *   Test comprehension of the "Needs Review" fallback states vs. definitive Pass/Fail signals.
    *   Design and iterate on an accessible, high-contrast UI based on survey feedback.
*   **Existing Coverage:** 
    *   The Agent Interviews highlight the stark contrast between agent tech-literacy (e.g., "Dave prints emails" vs "Jenny is fresh out of college").
    *   `docs/AssumptionsAndConstraints.md` explicitly mandates a UI that is "dead simple, intuitive, and requires no training".

## 2. Added Support for Wines and Malts
**Goal:** Expand the prototype's compliance coverage beyond Distilled Spirits to all major beverage classes.
*   **Justification:** Distilled spirits are only a subset of the ~150,000 annual applications. To provide comprehensive agency-wide value, the system must scale to handle the specific regulatory nuances (e.g., vintage, appellations) of all alcohol types.
*   **Action Items:**
    *   Analyze the BAM for Wine and Malt Beverages to extract deterministic rules (e.g., mandatory appellations of origin, sulfite declarations).
    *   Implement new rule dictionaries mirroring the structure of `distilled_spirits_label_rule_dicts.py`.
    *   Update the unified schema to accommodate fields specific to wine/malt (e.g., vintage, varietal).
*   **Existing Coverage:** 
    *   `docs/ExtensibilityGuide.md` details the exact technical process for adding rules and validation logic for new beverage classes.
    *   Project assumptions and `docs/AssumptionsAndConstraints.md` acknowledge that the current prototype intentionally limits scope to Distilled Spirits.

## 3. UX for Bulk Processing
**Goal:** Accommodate "peak season" volume drops (200-300 applications) seamlessly.
*   **Justification:** Importers frequently submit large batches of applications at once. Forcing agents to process these one-by-one is a severe bottleneck that negates the speed advantages of automation.
*   **Action Items:**
    *   Develop a frontend drag-and-drop interface capable of accepting bulk zip files or multi-select uploads.
    *   Implement an asynchronous "Report View" dashboard that allows agents to monitor batch progress and filter by "Needs Review" or "Failed".
*   **Existing Coverage:** 
    *   `docs/CriticalAnalysis.md` covers this extensively under "Asynchronous Bulk Processing capability," noting that the backend Celery + Redis architecture is *already* built to support this load, making the UI an integration task rather than a rewrite.
    *   The Agent Interviews explicitly call out the pain point of importers dumping large application batches.

## 4. COLA Integration via Webhook Signaling
**Goal:** Transition from a manual upload tool to an automated, invisible ingestion pipeline.
*   **Justification:** Manual uploads require agents to actively pull files and context-switch. Automated upstream ingestion transforms the system from a manual chore into a passive reporting tool, eliminating wait times entirely.
*   **Action Items:**
    *   Expose secure, authenticated webhook endpoints for the COLA system to push new application payloads immediately upon submission by importers.
    *   Design a callback mechanism (e.g., SNS/SQS or direct webhook return) to post compliance results back to the COLA agent dashboard.
*   **Existing Coverage:** 
    *   Discovery notes emphasize that automated ingestion from COLA is the superior "real-world workflow" compared to manual uploads.
    *   `docs/EnterpriseDeploymentAndSecurity.md` covers "COLA API integration strategies".
    *   `docs/CriticalAnalysis.md` notes that successful COLA ingestion makes the strict 5-second manual latency requirement irrelevant.

## 5. Formalized AI Pipeline Architecture (Sync/Async Job Orchestration)
**Goal:** Unify the synchronous data extraction steps with asynchronous long-running tasks into a cohesive, managed pipeline.
*   **Justification:** Managing multiple interdependent OCR and LLM steps via basic thread pools is brittle at scale. A formalized pipeline (like AWS Step Functions or Celery DAGs) ensures reliable retries, precise error isolation, and better observability.
*   **Action Items:**
    *   Transition from basic Celery tasks to directed acyclic graph (DAG) execution (e.g., Celery Canvas/Chords or AWS Step Functions) to formalize steps: `Image Ingestion -> OCR -> LLM Parsing -> Rule Evaluation`.
    *   Implement WebSocket or SSE (Server-Sent Events) on the frontend for real-time pipeline status updates, replacing aggressive polling.
*   **Existing Coverage:** 
    *   `docs/Architecture.md` already defines the core decoupled pattern (FastAPI + Celery + Redis).
    *   `docs/CriticalAnalysis.md` details how isolating async tasks inside the 5-second latency bound was achieved using parallel ThreadPools within the worker.

## 6. Improved Models - Dedicated CNN / Computer Vision
**Goal:** Move beyond basic text extraction to perform visual layout validation (e.g., verifying font size, bolding, and placement).
*   **Justification:** Text-based LLMs cannot reliably verify strict physical layout requirements (like the Government Warning being bold and properly contrasted) or handle heavily distorted bottle photos. A dedicated computer-vision model is required to bridge the gap between text equivalence and visual compliance.
*   **Action Items:**
    *   Train or fine-tune a Convolutional Neural Network (CNN) specifically on TTB layout rules to identify the exact bounding box and contrast of the Government Warning.
    *   Implement an advanced image pre-processing pipeline for real-world photos (perspective correction, deskewing, glare removal).
*   **Existing Coverage:** 
    *   `docs/CriticalAnalysis.md` (Gaps, Risks, and Future Considerations) explicitly identifies that visual formatting and imperfect photos require a "dedicated computer-vision model trained specifically on TTB layout rules".
    *   Project assumptions explicitly state that "Full visual TTB rule validation would require enhanced OCR with layout metadata or a dedicated computer-vision model."

## 7. Other Strategic Enhancements
*   **FedRAMP & Azure Migration:** Swap public OpenAI endpoints for Azure OpenAI within a secure VNet boundary to satisfy strict federal outbound traffic policies (Covered in `docs/CriticalAnalysis.md` and `docs/EnterpriseDeploymentAndSecurity.md`).
*   **Identity & Access Management (IAM):** Integrate the prototype with the agency's Active Directory / SAML provider for secure SSO, replacing the open prototype access (Covered in `docs/EnterpriseDeploymentAndSecurity.md`).
