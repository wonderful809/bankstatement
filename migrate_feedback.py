"""
Migration script to add Feedback table to existing database
Run this once to create the feedback table
"""
from app_saas import app, db
from models import Feedback

def migrate():
    with app.app_context():
        # Create feedback table if it doesn't exist
        db.create_all()
        print("✅ Migration complete! Feedback table created.")
        print(f"📊 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")

if __name__ == '__main__':
    print("🔄 Starting migration...")
    migrate()
    print("🎉 Done!")
