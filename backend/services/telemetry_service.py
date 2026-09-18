import time
from services.db_service import get_db
from models.models import AgentTelemetry

class TelemetryService:
    @staticmethod
    def log_call(agent_name: str, provider: str, model_name: str, latency_ms: float, 
                 prompt_tokens: int = 0, completion_tokens: int = 0, 
                 success: bool = True, error_message: str = None):
        """Logs an LLM interaction to the PostgreSQL database for observability."""
        try:
            # Get a database session
            db_gen = get_db()
            db = next(db_gen)
            
            # Simple Cost Calculator
            cost = 0.0
            if "gpt-4o-mini" in model_name or "mini" in model_name:
                cost = (prompt_tokens * 0.150 / 1_000_000) + (completion_tokens * 0.600 / 1_000_000)
            elif "70b" in model_name.lower():
                cost = (prompt_tokens * 0.59 / 1_000_000) + (completion_tokens * 0.80 / 1_000_000)
            elif "4o" in model_name:
                cost = (prompt_tokens * 5.0 / 1_000_000) + (completion_tokens * 15.0 / 1_000_000)
            else:
                # Fallback estimate
                cost = (prompt_tokens + completion_tokens) * 0.50 / 1_000_000
                
            telemetry_record = AgentTelemetry(
                agent_name=agent_name,
                provider=provider,
                model_name=model_name,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                total_cost=cost,
                success=1 if success else 0,
                error_message=error_message
            )
            db.add(telemetry_record)
            db.commit()
            db.close()
            # print(f" Telemetry Logged: {agent_name} via {provider} ({latency_ms:.2f}ms)")
        except Exception as e:
            print(f" Failed to log telemetry: {e}")
