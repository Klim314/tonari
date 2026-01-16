
from app.db import SessionLocal
from app.models import Work
from sqlalchemy import text

def check_db():
    try:
        with SessionLocal() as db:
            # Check if tables exist
            try:
                count = db.query(Work).count()
                print(f"Works count: {count}")
            except Exception as e:
                print(f"Error checking Works: {e}")
                
            # List all tables to see if they were dropped
            result = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';"))
            tables = [row[0] for row in result]
            print(f"Tables: {tables}")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_db()
