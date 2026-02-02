#!/usr/bin/env python3
"""
Script to update categories for existing leads that are currently uncategorized
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Lead
from main import extract_category_from_text

def update_lead_categories():
    """Update categories for all leads that are currently uncategorized"""
    db = SessionLocal()
    
    try:
        # Get all leads that don't have a category or are "Uncategorized"
        uncategorized_leads = db.query(Lead).filter(
            (Lead.category == None) | (Lead.category == "") | (Lead.category == "Uncategorized")
        ).all()
        
        print(f"Found {len(uncategorized_leads)} uncategorized leads")
        
        updated_count = 0
        category_counts = {}
        
        for lead in uncategorized_leads:
            # Extract category from title and description
            new_category = extract_category_from_text(
                lead.title or "", 
                lead.description or "", 
                lead.platform or ""
            )
            
            # Update the lead
            lead.category = new_category
            
            # Track statistics
            if new_category not in category_counts:
                category_counts[new_category] = 0
            category_counts[new_category] += 1
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"Updated {updated_count} leads...")
        
        # Commit all changes
        db.commit()
        
        print(f"\n✅ Successfully updated {updated_count} leads!")
        print("\n📊 Category distribution:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count} leads")
        
    except Exception as e:
        print(f"❌ Error updating categories: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Starting category update for existing leads...")
    update_lead_categories()
    print("✅ Category update complete!")