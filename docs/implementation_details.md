# Implementation Specification: BA Agent Pro

## Document Metadata
| Field | Value |
| :--- | :--- |
| **Version** | 1.1.0-STABLE |
| **Status** | Production-Ready |
| **Classification** | Internal / Confidential |
| **Technology Stack** | FastAPI, React, PostgreSQL, ChromaDB, Llama 3.1 |

---

## 1. Executive Summary
This document provides a comprehensive technical specification for the BA Agent Pro platform. It details the implementation of multi-agent orchestration, RAG-based context injection, and enterprise-grade security guardrails designed for high-stakes business analysis and discovery.

## 2. Infrastructure & Environment Configuration

### 2.1 System Prerequisites
- **Runtime**: Python 3.10+, Node.js 18+
- **Database**: Azure Database for PostgreSQL (Flexible Server)
- **Vector Store**: ChromaDB (Containerized on ACI)
- **Models**: Groq (Llama 3.1 70b), Azure OpenAI (GPT-4o)

### 2.2 Environment Variables (.env)
```ini
DATABASE_URL=postgresql://user:pass@host:port/dbname
ADO_ORG_URL=https://dev.azure.com/<org>
ADO_PROJECT=<project_name>
ADO_CREDENTIAL=<set_in_environment>
GROQ_CREDENTIAL=<set_in_environment>

AZURE_ACS_CONNECTION_STRING=<set_in_environment>
```

---

## 3. Core Agentic Orchestration Logic

### 3.1 The RequifyOrchestrator
The `RequifyOrchestrator` acts as the Central Nervous System, managing the state machine for each discovery session.

- **State Persistence**: Uses a `ProjectState` object cached in memory for high-speed retrieval, with periodic synchronization to the PostgreSQL `analyses` table.
- **Parallel Task Execution**: Utilizes `asyncio.gather` for non-dependent tasks (e.g., generating a Process Flow while performing Gap Analysis) to minimize BA wait time.
- **Contextual Injection**: Before any LLM call, the Orchestrator queries the `ProjectContext` (DNA) to inject LOB-specific constraints into the prompt prefix.

### 3.2 Modular Toolkit Mode
The system supports surgical execution via the `enabled_modules` flag.
- **Input**: `['gaps', 'trd', 'flow', 'backlog']`
- **Execution**: The orchestrator evaluates the list and only instantiates the required agents, drastically reducing operational token cost and latency.

---

## 4. Security & Data Sovereignty

### 4.1 Zero-Knowledge Privacy Shield
The `GuardAgent` implements a surgical redaction layer before any data leaves the secure environment.
- **Regex Patterns**:
    - **Email**: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` ➔ `[EMAIL_REDACTED]`
    - **Phone**: `\b\d{3}[-.]?\d{3}[-.]?\d{4}\b` ➔ `[PHONE_REDACTED]`
    - **Credentials**: `(?i)(password|secret|key|token|auth)\s*[:=]\s*[^\s]+` ➔ `[SECRET_REDACTED]`
- **Implementation**: The Orchestrator wraps the raw `project.extraction` in a `mask_pii` call before passing it to any external API.

### 4.2 Governance Vault (Audit Logs)
Every Azure DevOps synchronization event is serialized into a JSON payload and stored in the `audit_logs` table.
- **Schema**:
    - `action`: Type of synchronization (e.g., SYNC_TO_ADO).
    - `actor`: The authenticated user (currently admin).
    - `details`: JSON payload containing the count of items created/updated and their specific Remote IDs.
    - `analysis_id`: Foreign key link to the discovery session.

---

## 5. Data Models & API Contracts

### 5.1 Primary Database Schema (SQLAlchemy)
```python
class Analysis(Base):
    id = Column(String, primary_key=True)
    status = Column(String) # IN_PROGRESS, COMPLETED, FAILED
    trd_content = Column(Text)
    backlog_json = Column(JSON)
    lob = Column(String)
    created_at = Column(DateTime)

class AuditLog(Base):
    id = Column(Integer, primary_key=True)
    action = Column(String)
    details = Column(Text) # Serialized JSON
    analysis_id = Column(String, ForeignKey('analyses.id'))
```

### 5.2 RAG Integration (ChromaDB)
- **Collection Name**: `project_dna`
- **Embedding Model**: `text-embedding-3-small` (Azure OpenAI)
- **Logic**: During the "Initialize" phase, the `ContextAgent` performs a similarity search against the selected LOB to retrieve the top 3 relevant technical constraints or definitions.

---

## 6. Integration Protocols

### 6.1 Azure DevOps (ADO) Sync
- **Service**: `AzureDevOpsService`
- **Method**: Selective JSON-Patch (`application/json-patch+json`)
- **Upsert Strategy**: 
    - If `remote_id` exists: `PATCH /_apis/wit/workitems/{id}`
    - If `remote_id` is null: `POST /_apis/wit/workitems/${type}`
- **Parental Linking**: Uses `System.Link` to establish Epic ➔ Feature ➔ Story hierarchy.

### 6.2 Azure Communication Services (ACS)
- **Payload**: Branded HTML template with embedded TRD snippets.
- **Protocol**: HTTPS REST over ACS SDK.

---

## 7. Operations & Maintenance
- **Logging**: Standard Python `logging` module configured with `StreamHandler` for Azure App Service log streaming.
- **Monitoring**: Integration with **Application Insights** for tracking AI latency and token exhaustion alerts.
- **Scalability**: Stateless backend design allows for horizontal scaling across multiple App Service instances.
