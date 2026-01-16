import sys
import os

# Add backend directory to path so we can import app modules
sys.path.append(os.getcwd())

from sqlalchemy import func, select, delete
from app.db import SessionLocal
from app.models import Chapter

def cleanup_duplicates():
    with SessionLocal() as db:
        # Find duplicates: group by work_id, sort_key and count > 1
        stmt = (
            select(Chapter.work_id, Chapter.sort_key, func.count(Chapter.id))
            .group_by(Chapter.work_id, Chapter.sort_key)
            .having(func.count(Chapter.id) > 1)
        )
        duplicates = db.execute(stmt).all()
        
        print(f"Found {len(duplicates)} sets of duplicates")
        
        total_deleted = 0
        for work_id, sort_key, count in duplicates:
            # Get all chapters for this work/key tuple
            chapters = db.scalars(
                select(Chapter)
                .where(Chapter.work_id == work_id, Chapter.sort_key == sort_key)
                .order_by(Chapter.id.desc()) # Keep the latest one usually, or oldest? 
                # Actually, let's keep the one with the highest ID (latest scrape) 
                # assuming it might have better data, or just arbitrary since they are dupes.
            ).all()
            
            # Keep the first one (latest ID), delete the rest
            to_keep = chapters[0]
            to_delete = chapters[1:]
            
            print(f"Work {work_id} Ch {sort_key}: Keeping ID {to_keep.id}, deleting IDs {[c.id for c in to_delete]}")
            
            for chap in to_delete:
                db.delete(chap)
                total_deleted += 1
                
        db.commit()
        print(f"Deleted {total_deleted} duplicate chapters")

if __name__ == "__main__":
    cleanup_duplicates()
