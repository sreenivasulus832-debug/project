"""
init_db.py
Run this script once to create the database tables and populate sample records.
Usage:
    python init_db.py
"""

from database import init_db

if __name__ == "__main__":
    print("Initializing SQLite database for Online Voting System...")
    init_db(seed_data=True)
    print("\nDatabase initialization complete! You can now run 'python app.py'.")
