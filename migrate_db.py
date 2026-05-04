from app import app, db, User, QuizResult
import os

with app.app_context():
    # We use raw SQL because SQLAlchemy's create_all doesn't handle migrations
    try:
        db.session.execute(db.text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
        print("Added is_admin to users table")
    except Exception as e:
        print(f"Note: {e}")

    try:
        db.session.execute(db.text("ALTER TABLE quiz_results ADD COLUMN difficulty VARCHAR(20) DEFAULT 'Moderate'"))
        print("Added difficulty to quiz_results table")
    except Exception as e:
        print(f"Note: {e}")

    # Set existing admin user
    admin_email = os.getenv("ADMIN_EMAIL", "admin@careerpath.ai")
    admin = User.query.filter_by(email=admin_email).first()
    if admin:
        admin.is_admin = True
        db.session.commit()
        print(f"User {admin.username} set as admin")
    else:
        print(f"Admin user with email {admin_email} not found")

    db.session.commit()
