import os
from sqlalchemy import text
from services.db_service import engine

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN project_id VARCHAR"))
            print("Added project_id to documents.")
        except Exception as e:
            print(f"documents table error: {e}")
            
        try:
            conn.execute(text("ALTER TABLE analyses ADD COLUMN project_id VARCHAR"))
            print("Added project_id to analyses.")
        except Exception as e:
            print(f"analyses table error: {e}")
            
        try:
            conn.execute(text("ALTER TABLE approvals ADD COLUMN project_id VARCHAR"))
            print("Added project_id to approvals.")
        except Exception as e:
            print(f"approvals table error: {e}")
            
        conn.commit()

if __name__ == '__main__':
    add_columns()
