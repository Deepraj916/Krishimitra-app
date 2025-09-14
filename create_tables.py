# create_tables.py

from app import app, db

# This script's only purpose is to create the database tables.
with app.app_context():
    print("Connecting to the database and creating tables...")
    db.create_all()
    print("Database tables created successfully.")