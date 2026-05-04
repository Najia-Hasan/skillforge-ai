from app import app, db, CareerRoadmap
import json

with app.app_context():
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        # Check if table exists and can be queried
        count = CareerRoadmap.query.count()
        print(f"Table 'career_roadmaps' exists. Current record count: {count}")
        
        # Check columns for users
        columns_users = [c['name'] for c in inspector.get_columns('users')]
        print(f"Columns in 'users': {columns_users}")
        
        # Check columns for quiz_results
        columns_quiz = [c['name'] for c in inspector.get_columns('quiz_results')]
        print(f"Columns in 'quiz_results': {columns_quiz}")
        
    except Exception as e:
        print(f"Error checking table: {e}")
        print("Attempting to create all tables...")
        db.create_all()
        print("Tables created.")
