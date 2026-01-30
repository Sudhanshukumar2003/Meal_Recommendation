import sqlite3

conn = sqlite3.connect('/app/backend/data/users.db')
cursor = conn.cursor()

# Check existing tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Existing tables:", tables)

# Create meal_feedback table if it doesn't exist
if 'meal_feedback' not in tables:
    print("Creating meal_feedback table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipe_name TEXT NOT NULL,
            meal_type TEXT,
            rating INTEGER NOT NULL,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    print("meal_feedback table created successfully!")
else:
    print("meal_feedback table already exists")

# Verify the table was created
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables after creation:", tables)

conn.close()
