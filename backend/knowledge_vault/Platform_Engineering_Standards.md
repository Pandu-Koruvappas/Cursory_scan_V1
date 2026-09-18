# BA Agent Pro: Official Engineering & Domain Standards

This document serves as the primary 'Source of Truth' for all discovery and architecting actions performed by the BA Agent Pro platform.

## 1. The Five Resilience Pillars (Mandatory Compliance)
Every artifact generated must adhere to these quality gates:
- **Pillar 1: Proactive Quality Gating**: No requirement is accepted without a Quality Score assessment.
- **Pillar 2: Adversarial Critique**: Every TRD and Backlog must pass through the Critic Agent for hallucination checks.
- **Pillar 3: Human-in-the-Loop (HITL)**: All engineering syncs to Azure DevOps require a formal human approval gate.
- **Pillar 4: Persistent Project DNA**: Context must be grounded in the historical Tech Stack and Project Preferences.
- **Pillar 5: Autonomous Reflection**: Agents must self-correct if the Critic's confidence score is below 85%.

## 2. P&C Insurance Domain Mandates
Requirements must align with standard Property & Casualty insurance workflows:
- **Policy Lifecycle**: Must account for Quote, Bind, Issuance, Endorsement, and Renewal.
- **Claims Processing**: Must identify First Notice of Loss (FNOL), Adjudication, and Settlement.
- **Compliance**: All systems must adhere to local regulatory data residency and encryption standards.

## 3. Azure DevOps (ADO) Hierarchy Standards
The platform enforces a strict hierarchy for backlog engineering:
- **EPIC**: High-level business objective (e.g., 'Modernize Claims Portal').
- **FEATURE**: Sub-objective tied to a specific capability.
- **USER STORY**: Atomic unit of work. Must include 'As a... I want... So that...' and explicit 'Acceptance Criteria'.

## 4. Technical Architecture Standards
- **APIs**: Must be RESTful, documented with OpenAPI (FastAPI), and include robust error handling.
- **Frontend**: Modern React architecture using functional components and hooks.
- **Security**: Mandatory PII masking for all external LLM transmissions (handled by GuardAgent).
