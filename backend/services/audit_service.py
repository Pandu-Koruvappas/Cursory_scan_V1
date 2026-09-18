import json
from datetime import datetime
from services.db_service import SessionLocal
from models.models import AuditLog

class AuditService:
    """
    Enterprise Governance Service.
    Handles the immutable logging of agent decisions and reasoning.
    """
    @staticmethod
    def log_action(document_id: str, agent_name: str, action: str, reasoning: str, payload: dict = None):
        """
        Records a significant agent action into the audit trail.
        """
        db = SessionLocal()
        try:
            log_entry = AuditLog(
                document_id=document_id,
                agent_name=agent_name,
                action=action,
                reasoning=reasoning,
                decision_payload=payload
            )
            db.add(log_entry)
            db.commit()
            print(f"--- [AUDIT] {agent_name} recorded action: {action} ---")
        except Exception as e:
            print(f"CRITICAL: Failed to write to Audit Log: {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def get_logs(document_id: str):
        """
        Retrieves the full audit history for a specific project.
        """
        db = SessionLocal()
        try:
            return db.query(AuditLog).filter(AuditLog.document_id == document_id).order_by(AuditLog.timestamp.desc()).all()
        finally:
            db.close()
