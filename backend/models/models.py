from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from services.db_service import Base
from datetime import datetime, timezone

class Document(Base):
    """Document model for storing uploaded files"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    user_email = Column(String, nullable=False, default="guest")
    project_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_path = Column(String, nullable=False)
    content = Column(Text)
    meta = Column(JSON)
    status = Column(String, default="uploaded")

class Analysis(Base):
    """Analysis model for storing analysis results"""
    __tablename__ = "analyses"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="completed")
    original_text = Column(Text)
    results = Column(JSON) # Legacy column
    
    # Explicit structured columns
    extraction = Column(JSON)
    gaps = Column(JSON)
    functional_spec = Column(JSON)
    backlog = Column(JSON)
    test_cases = Column(JSON)
    reviews = Column(JSON)
    diagram = Column(JSON)
    critic_review = Column(JSON)
    
    document_id = Column(String)
    user_email = Column(String)
    project_id = Column(String, nullable=True)

class Approval(Base):
    """Approval model for tracking approval workflow"""
    __tablename__ = "approvals"
    
    id = Column(String, primary_key=True)
    analysis_id = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    approver_email = Column(String)
    results_summary = Column(JSON)
    approver_response = Column(String)
    ado_result = Column(JSON)

class ProjectContext(Base):
    """Stores persistent project DNA (Tech Stack, Preferences, Knowledge) to minimize AI load"""
    __tablename__ = "project_context"
    
    id = Column(String, primary_key=True) 
    dna_type = Column(String, primary_key=True, default="GENERAL") # TECH_STACK, PREFERENCES, GLOSSARY, STAKEHOLDERS
    context_text = Column(Text, nullable=False)
    weight = Column(Integer, default=1) # Importance weight for LLM context injection
    last_scan_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    project_metadata = Column(JSON)

class AuditLog(Base):
    """Governance Vault: Tracks all critical agent actions for enterprise compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String, ForeignKey("project_states.document_id")) # Linked to Orchestrator Project
    agent_name = Column(String) # e.g., "SecurityAgent", "Architect"
    action = Column(String, nullable=False) # e.g., "RISK_FLAGGED", "SYNC_TO_ADO"
    reasoning = Column(Text) # The 'Why' behind the decision
    decision_payload = Column(JSON) # The actual output/recommendation
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    project = relationship("ProjectStateModel", back_populates="audit_logs")

class ProjectStateModel(Base):
    """Persistent state for the Requify multi-agent orchestrator"""
    __tablename__ = "project_states"
    
    project_id = Column(String, primary_key=True)
    document_id = Column(String, index=True)
    lob = Column(String, default="General")
    status = Column(String, default="INITIALIZED")
    history = Column(JSON, default=list)
    
    extraction = Column(JSON, nullable=True)
    gaps = Column(JSON, nullable=True)
    trd = Column(Text, nullable=True)
    backlog = Column(JSON, nullable=True)
    reviews = Column(JSON, default=dict)
    diagram = Column(JSON, nullable=True)
    quality_score = Column(Float, default=0.0)
    critic_reviews = Column(JSON, default=dict)
    ambiguity_report = Column(JSON, nullable=True)
    
    # Audit Trail Relationship
    audit_logs = relationship("AuditLog", back_populates="project")
    
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def update_status(self, new_status: str, message: str):
        self.status = new_status
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": new_status,
            "message": message
        }
        # Re-assign list to trigger SQLAlchemy JSON mutation detection
        current_history = list(self.history) if self.history else []
        current_history.append(new_entry)
        self.history = current_history
        self.last_updated = datetime.now(timezone.utc)

class AgentTelemetry(Base):
    """Observability: Tracks performance, cost, and usage of every LLM call"""
    __tablename__ = "telemetry_logs"
    
    id = Column(Integer, primary_key=True)
    agent_name = Column(String, index=True, default="unknown") # E.g., "AutomationAgent"
    provider = Column(String) # groq, azure"
    model_name = Column(String)
    latency_ms = Column(Float, default=0.0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    success = Column(Integer, default=1) # 1 = Success, 0 = Failed
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
