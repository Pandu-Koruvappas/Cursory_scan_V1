import os
import sys
from sqlalchemy import text

# Ensure backend is in path
sys.path.append(os.getcwd())

from backend.services.db_service import SessionLocal

def migrate():
    print("--- Upgrading Project DNA Schema ---")
    db = SessionLocal()
    try:
        # Add dna_type column
        print("Adding 'dna_type' column...")
        db.execute(text("ALTER TABLE project_context ADD COLUMN IF NOT EXISTS dna_type VARCHAR DEFAULT 'GENERAL'"))
        
        # Add weight column
        print("Adding 'weight' column...")
        db.execute(text("ALTER TABLE project_context ADD COLUMN IF NOT EXISTS weight INTEGER DEFAULT 1"))
        
        db.commit()
        print("Migration Successful.")
    except Exception as e:
        print(f"Migration Failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
