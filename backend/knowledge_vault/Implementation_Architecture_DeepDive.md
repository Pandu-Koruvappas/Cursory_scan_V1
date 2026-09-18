# BA Agent Pro: Implementation Architecture Deep-Dive

This document codifies the technical internal mechanics and architectural patterns of the BA Agent Pro platform.

## 1. Multi-Agent Orchestration Pattern
The platform utilizes a **Generative-Adversarial (GA) Architecture**:
- **RequifyOrchestrator**: The central state-machine and decision engine.
- **Spec Architect (TRDGen)**: Responsible for 'Generative' creation of technical specifications.
- **Critic Agent**: Responsible for 'Adversarial' QA. 
- **The Reflection Loop**: An autonomous recursive logic where the Architect must address Critic feedback if the confidence score < 85%.

## 2. High-Density UI/UX Design Language
The frontend (React) follows a 'Command Center' aesthetic:
- **Typographic First**: Minimalist, high-readability fonts (Inter/Outfit).
- **Glassmorphism**: Subtle translucent layers for high-fidelity UI depth.
- **Dynamic Feedback**: Real-time 'Honest AI' panels showing Quality Scores and Critic findings.
- **Interactive Workbench**: A gated approval workflow for Azure DevOps synchronization.

## 3. Data Persistence & State Management
- **PostgreSQL**: Used for all project state, audit logs, and institutional memory.
- **Project DNA Vault**: A structured repository of project-specific tech stacks and preferences stored in the `project_context` table.
- **ChromaDB**: High-performance vector database used for Semantic RAG (Institutional Knowledge).

## 4. Azure DevOps (ADO) Integration Logic
- **Stateful Mapping**: Requirements are mapped to ADO Work Items using a parent-child linking strategy.
- **Hierarchy Enforcement**: Epic -> Feature -> User Story.
- **Human-Gated Sync**: No data is pushed to ADO without a formal `/sync-backlog` POST request triggered by human approval.

## 5. Resilience & Quality Scoring
- **Extraction Scoring**: Initial requirements are scored 0-10 based on clarity, completeness, and feasibility.
- **Adversarial Gate**: TRDs are blocked from completion until the Critic Agent confirms no 'Hallucinations' or 'Contradictions' relative to the source BRD.
