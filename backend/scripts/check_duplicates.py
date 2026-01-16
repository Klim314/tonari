import sys
import os

# Add backend directory to path so we can import app modules
sys.path.append(os.getcwd())

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from app.db import SessionLocal
from app.models import Chapter

def check_duplicates():
    with SessionLocal() as db:
        # Find duplicates: group by work_id, sort_key and count > 1
        stmt = (
            select(Chapter.work_id, Chapter.sort_key, func.count(Chapter.id))
            .group_by(Chapter.work_id, Chapter.sort_key)
            .having(func.count(Chapter.id) > 1)
        )
        duplicates = db.execute(stmt).all()
        
        print(f"Found {len(duplicates)} sets of duplicates")
        
        duplicates_with_translations = 0
        total_dup_chapters = 0
        
        for work_id, sort_key, count in duplicates:
            # Get all chapters for this work/key tuple, eagerly load translations
            chapters = db.scalars(
                select(Chapter)
                .where(Chapter.work_id == work_id, Chapter.sort_key == sort_key)
                .options(selectinload(Chapter.translations))
                .order_by(Chapter.id.desc())
            ).all()
            
            print(f"--- Group: Work {work_id}, Sort Key {sort_key} ({len(chapters)} chapters) ---")
            for chap in chapters:
                print(f"  ID: {chap.id}, Translations: {len(chap.translations)}")
                if len(chap.translations) > 0:
                     duplicates_with_translations += 1
            
            total_dup_chapters += (len(chapters) - 1)

        print(f"\nSummary:")
        print(f"Total duplicate sets: {len(duplicates)}")
        print(f"Total redundant chapters to delete: {total_dup_chapters}")
        print(f"Chapters in duplicate sets that have translations: {duplicates_with_translations}")

if __name__ == "__main__":
    check_duplicates()
