import sqlite3
from datetime import datetime
import hashlib
import secrets
import os
import json
from email_service import send_otp_both


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'users.db')
        self.db_path = db_path
        self.init_db()
        self.migrate_db()  # Run migrations after initialization
    
    def migrate_db(self):
        """Run database migrations"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if phone_verified column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'phone_verified' not in columns:
                print("Running migration: Adding phone_verified column...")
                cursor.execute("ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0")
                conn.commit()
                print("Migration completed: phone_verified column added")
            
            # Check if reset_code column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'reset_code' not in columns:
                print("Running migration: Adding reset_code column...")
                cursor.execute("ALTER TABLE users ADD COLUMN reset_code TEXT")
                conn.commit()
                print("Migration completed: reset_code column added")
            
            # Check if reset_code_expires column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'reset_code_expires' not in columns:
                print("Running migration: Adding reset_code_expires column...")
                cursor.execute("ALTER TABLE users ADD COLUMN reset_code_expires TIMESTAMP")
                conn.commit()
                print("Migration completed: reset_code_expires column added")
            
            # Check if google_oauth column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'google_oauth' not in columns:
                print("Running migration: Adding google_oauth column...")
                cursor.execute("ALTER TABLE users ADD COLUMN google_oauth TEXT DEFAULT NULL")
                conn.commit()
                print("Migration completed: google_oauth column added")
            
            # Check if preferred_cuisine column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'preferred_cuisine' not in columns:
                print("Running migration: Adding preferred_cuisine column...")
                cursor.execute("ALTER TABLE users ADD COLUMN preferred_cuisine TEXT DEFAULT 'Any'")
                conn.commit()
                print("Migration completed: preferred_cuisine column added")

            # Ensure meal_plans table exists for persisting last generated plan
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meal_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    plan_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()

            # Add columns to meal_feedback if missing
            cursor.execute("PRAGMA table_info(meal_feedback)")
            feedback_columns = [column[1] for column in cursor.fetchall()]

            if 'preference' not in feedback_columns:
                print("Running migration: Adding preference column to meal_feedback...")
                cursor.execute("ALTER TABLE meal_feedback ADD COLUMN preference TEXT")
                conn.commit()
                print("Migration completed: preference column added")

            if 'skipped' not in feedback_columns:
                print("Running migration: Adding skipped column to meal_feedback...")
                cursor.execute("ALTER TABLE meal_feedback ADD COLUMN skipped INTEGER DEFAULT 0")
                conn.commit()
                print("Migration completed: skipped column added")
            
        except Exception as e:
            print(f"Migration error: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database with users table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                phone_number TEXT,
                phone_verified INTEGER DEFAULT 0,
                age INTEGER,
                height REAL,
                weight REAL,
                gender TEXT,
                health_goals TEXT,
                preferred_diet_type TEXT,
                allergies TEXT,
                health_conditions TEXT,
                activity_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_used INTEGER DEFAULT 0,
                FOREIGN KEY (username) REFERENCES users (username)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recipe_name TEXT NOT NULL,
                meal_type TEXT,
                rating INTEGER NOT NULL,
                preference TEXT,
                skipped INTEGER DEFAULT 0,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()

    def save_latest_meal_plan(self, user_id: int, plan_data: dict) -> bool:
        """Upsert the latest meal plan for a user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            plan_json = json.dumps(plan_data)
            cursor.execute(
                """
                INSERT INTO meal_plans (user_id, plan_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    plan_json = excluded.plan_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, plan_json)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving meal plan: {e}")
            return False

    def get_latest_meal_plan(self, user_id: int):
        """Retrieve the latest saved meal plan for a user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT plan_json FROM meal_plans WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            return json.loads(row[0]) if row[0] else None
        except Exception as e:
            print(f"Error fetching meal plan: {e}")
            return None

    def hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username: str, email: str, password: str, full_name: str = None, 
                   phone_number: str = None, age: int = None, height: float = None, weight: float = None, 
                   gender: str = None, health_goals: list = None, preferred_diet_type: str = None,
                   preferred_cuisine: str = "Any", allergies: list = None, health_conditions: list = None, activity_level: str = None):
        """Create a new user with profile information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            
            # Convert lists to JSON strings
            import json
            health_goals_str = json.dumps(health_goals) if health_goals else None
            allergies_str = json.dumps(allergies) if allergies else None
            health_conditions_str = json.dumps(health_conditions) if health_conditions else None
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, phone_number, age, height, 
                                 weight, gender, health_goals, preferred_diet_type, preferred_cuisine,
                                 allergies, health_conditions, activity_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, email, password_hash, full_name, phone_number, age, height, weight, 
                  gender, health_goals_str, preferred_diet_type, preferred_cuisine, allergies_str, health_conditions_str, activity_level))
            
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            return {"success": True, "user_id": user_id, "message": "User created successfully"}
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return {"success": False, "message": "Username already exists"}
            elif "email" in str(e):
                return {"success": False, "message": "Email already exists"}
            return {"success": False, "message": "User creation failed"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def authenticate_user(self, username: str, password: str):
        """Authenticate user with username and password"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            
            cursor.execute("""
                SELECT id, username, email, full_name, phone_number, age, height, weight,
                       gender, health_goals, preferred_diet_type, preferred_cuisine, allergies, 
                       health_conditions, activity_level
                FROM users
                WHERE username = ? AND password_hash = ?
            """, (username, password_hash))

            user = cursor.fetchone()

            if user:
                # Update last login
                cursor.execute("""
                    UPDATE users
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user['id'],))
                conn.commit()
                
                # Generate session token
                session_token = secrets.token_urlsafe(32)
                
                # Store session (expires in 24 hours)
                cursor.execute("""
                    INSERT INTO sessions (user_id, session_token, expires_at)
                    VALUES (?, ?, datetime('now', '+1 day'))
                """, (user['id'], session_token))
                
                conn.commit()
                conn.close()
                
                # Decode JSON fields
                import json

                def _decode(value):
                    if value is None:
                        return []
                    if isinstance(value, str):
                        try:
                            # Try to parse as JSON first
                            return json.loads(value)
                        except Exception:
                            # Fallback: treat as comma-separated string
                            return [item.strip() for item in value.split(',') if item.strip()]
                    return value
                
                return {
                    "success": True,
                    "user": {
                        "id": user['id'],
                        "username": user['username'],
                        "email": user['email'],
                        "full_name": user['full_name'],
                        "phone_number": user['phone_number'],
                        "age": user['age'],
                        "height": user['height'],
                        "weight": user['weight'],
                        "gender": user['gender'],
                        "activity_level": user['activity_level'],
                        "health_goals": _decode(user['health_goals']),
                        "preferred_diet_type": user['preferred_diet_type'],
                        "preferred_cuisine": user['preferred_cuisine'],
                        "allergies": _decode(user['allergies']),
                        "health_conditions": _decode(user['health_conditions'])
                    },
                    "session_token": session_token,
                    "message": "Login successful"
                }
            else:
                conn.close()
                return {"success": False, "message": "Invalid username or password"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def verify_session(self, session_token: str):
        """Verify session token and return full user data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT u.id, u.username, u.email, u.full_name, u.phone_number,
                       u.age, u.height, u.weight, u.gender, u.activity_level,
                       u.health_goals, u.preferred_diet_type, u.preferred_cuisine, 
                       u.allergies, u.health_conditions
                FROM users u
                JOIN sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.expires_at > datetime('now')
                """,
                (session_token,),
            )

            user = cursor.fetchone()
            conn.close()

            if not user:
                return {"success": False, "message": "Invalid or expired session"}

            # Decode JSON-like fields to Python lists for easier use downstream
            import json

            def _decode(value):
                if value is None:
                    return []
                if isinstance(value, str):
                    try:
                        # Try to parse as JSON first
                        return json.loads(value)
                    except Exception:
                        # Fallback: treat as comma-separated string
                        return [item.strip() for item in value.split(',') if item.strip()]
                return value

            return {
                "success": True,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "phone_number": user['phone_number'],
                    "age": user['age'],
                    "height": user['height'],
                    "weight": user['weight'],
                    "gender": user['gender'],
                    "activity_level": user['activity_level'],
                    "health_goals": _decode(user['health_goals']),
                    "preferred_diet_type": user['preferred_diet_type'],
                    "preferred_cuisine": user['preferred_cuisine'],
                    "allergies": _decode(user['allergies']),
                    "health_conditions": _decode(user['health_conditions']),
                },
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def create_session(self, user_id: int):
        """Create a session for the given user and return the token"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Generate session token
            session_token = secrets.token_urlsafe(32)

            # Store session (expires in 24 hours)
            cursor.execute(
                """
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (?, ?, datetime('now', '+1 day'))
                """,
                (user_id, session_token)
            )

            conn.commit()
            conn.close()

            return session_token
        except Exception as e:
            print(f"Error creating session: {e}")
            return None

    def logout(self, session_token: str):
        """Delete session token"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Logged out successfully"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def generate_otp(self, username: str):
        """Generate OTP for user and send via email/SMS"""
        try:
            # Check if user exists
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, email, phone_number, full_name FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {"success": False, "message": "Username not found"}
            
            # Generate 6-digit OTP
            otp_code = str(secrets.randbelow(999999)).zfill(6)
            
            # Store OTP (expires in 10 minutes)
            cursor.execute("""
                INSERT INTO otps (username, otp_code, expires_at)
                VALUES (?, ?, datetime('now', '+10 minutes'))
            """, (username, otp_code))
            
            conn.commit()
            conn.close()
            
            # Send OTP via email and/or SMS
            delivery_result = send_otp_both(
                email=user['email'],
                phone_number=user['phone_number'],
                otp_code=otp_code,
                recipient_name=user['full_name'] or username
            )
            
            return {
                "success": True,
                "message": f"OTP sent successfully via {delivery_result['delivery_method']}",
                "delivery_method": delivery_result['delivery_method'],
                "email_sent": delivery_result['email_sent'],
                "sms_sent": delivery_result['sms_sent']
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def verify_otp(self, username: str, otp_code: str):
        """Verify OTP and create session"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get valid OTP
            cursor.execute("""
                SELECT id FROM otps
                WHERE username = ? AND otp_code = ? 
                AND expires_at > datetime('now') AND is_used = 0
                ORDER BY created_at DESC
                LIMIT 1
            """, (username, otp_code))
            
            otp = cursor.fetchone()
            
            if not otp:
                conn.close()
                return {"success": False, "message": "Invalid or expired OTP"}
            
            # Mark OTP as used
            cursor.execute("UPDATE otps SET is_used = 1 WHERE id = ?", (otp['id'],))
            
            # Get user info
            cursor.execute("""
                SELECT id, username, email, full_name, phone_number, age, height, weight,
                       gender, health_goals, preferred_diet_type, preferred_cuisine, allergies, 
                       health_conditions, activity_level
                FROM users
                WHERE username = ?
            """, (username,))
            
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {"success": False, "message": "User not found"}
            
            # Update last login
            cursor.execute("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user['id'],))
            
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            
            # Store session (expires in 24 hours)
            cursor.execute("""
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (?, ?, datetime('now', '+1 day'))
            """, (user['id'], session_token))
            
            conn.commit()
            conn.close()
            
            # Decode JSON fields
            import json

            def _decode(value):
                if value is None:
                    return []
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except Exception:
                        return []
                return value
            
            return {
                "success": True,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "phone_number": user['phone_number'],
                    "age": user['age'],
                    "height": user['height'],
                    "weight": user['weight'],
                    "gender": user['gender'],
                    "activity_level": user['activity_level'],
                    "health_goals": _decode(user['health_goals']),
                    "preferred_diet_type": user['preferred_diet_type'],
                    "preferred_cuisine": user['preferred_cuisine'],
                    "allergies": _decode(user['allergies']),
                    "health_conditions": _decode(user['health_conditions'])
                },
                "session_token": session_token,
                "message": "Login successful"
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def send_phone_verification(self, username: str):
        """Send OTP for phone verification"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, phone_number, phone_verified FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {"success": False, "message": "User not found"}
            
            if not user['phone_number']:
                conn.close()
                return {"success": False, "message": "No phone number registered"}
            
            if user['phone_verified']:
                conn.close()
                return {"success": False, "message": "Phone already verified"}
            
            # Generate 6-digit OTP
            otp_code = str(secrets.randbelow(999999)).zfill(6)
            
            # Store OTP (expires in 10 minutes)
            cursor.execute("""
                INSERT INTO otps (username, otp_code, expires_at)
                VALUES (?, ?, datetime('now', '+10 minutes'))
            """, (username, otp_code))
            
            conn.commit()
            conn.close()
            
            # Send OTP via SMS
            from email_service import send_otp_sms
            sms_sent = send_otp_sms(user['phone_number'], otp_code)
            
            return {
                "success": True,
                "message": "OTP sent to your phone number",
                "phone_number": user['phone_number'][-4:],  # Last 4 digits only
                "sms_sent": sms_sent
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def verify_phone_otp(self, username: str, otp_code: str):
        """Verify phone number with OTP"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get valid OTP
            cursor.execute("""
                SELECT id FROM otps
                WHERE username = ? AND otp_code = ? 
                AND expires_at > datetime('now') AND is_used = 0
                ORDER BY created_at DESC
                LIMIT 1
            """, (username, otp_code))
            
            otp = cursor.fetchone()
            
            if not otp:
                conn.close()
                return {"success": False, "message": "Invalid or expired OTP"}
            
            # Mark OTP as used
            cursor.execute("UPDATE otps SET is_used = 1 WHERE id = ?", (otp['id'],))
            
            # Mark phone as verified
            cursor.execute("UPDATE users SET phone_verified = 1 WHERE username = ?", (username,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "Phone number verified successfully"
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def generate_password_reset_code(self, email: str):
        """Generate and send password reset code to email"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id, username, email FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {"success": False, "message": "Email not found"}
            
            # Generate 6-digit reset code
            reset_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            
            # Store reset code with 30-minute expiration
            cursor.execute("""
                UPDATE users
                SET reset_code = ?, reset_code_expires = datetime('now', '+30 minutes')
                WHERE email = ?
            """, (reset_code, email))
            
            conn.commit()
            conn.close()
            
            # Send email with reset code
            from email_service import send_password_reset_email
            email_sent = send_password_reset_email(email, user['username'], reset_code)
            
            return {
                "success": True,
                "message": "Password reset code sent to your email",
                "email": email,
                "email_sent": email_sent
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def verify_reset_code_and_update_password(self, email: str, reset_code: str, new_password: str):
        """Verify reset code and update password"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if reset code is valid
            cursor.execute("""
                SELECT id FROM users
                WHERE email = ? AND reset_code = ? AND reset_code_expires > datetime('now')
            """, (email, reset_code))
            
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {"success": False, "message": "Invalid or expired reset code"}
            
            # Hash new password
            password_hash = self.hash_password(new_password)
            
            # Update password and clear reset code
            cursor.execute("""
                UPDATE users
                SET password_hash = ?, reset_code = NULL, reset_code_expires = NULL
                WHERE email = ?
            """, (password_hash, email))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "Password reset successfully"
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    def get_or_create_google_user(self, email: str, username: str, full_name: str):
        """Get existing user or create new one from Google OAuth"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if user:
                conn.close()
                return {
                    "success": True,
                    "user_id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "is_new": False
                }
            
            # Create new user from Google OAuth
            cursor.execute("""
                INSERT INTO users (username, email, full_name, password_hash, google_oauth, phone_verified)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, email, full_name, "oauth_google", True, 1))
            
            conn.commit()
            new_user_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "user_id": new_user_id,
                "username": username,
                "email": email,
                "full_name": full_name,
                "is_new": True
            }
        except Exception as e:
            print(f"Error in get_or_create_google_user: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_user_by_id(self, user_id: int):
        """Get user details by user ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, email, full_name, phone_number, age, height, weight,
                       gender, health_goals, preferred_diet_type, preferred_cuisine, allergies, 
                       health_conditions, activity_level
                FROM users WHERE id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return None

            import json

            def _decode(value):
                if value is None:
                    return []
                if isinstance(value, str):
                    try:
                        # Try to parse as JSON first
                        return json.loads(value)
                    except Exception:
                        # Fallback: treat as comma-separated string
                        return [item.strip() for item in value.split(',') if item.strip()]
                return value

            return {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "full_name": user['full_name'],
                "phone_number": user['phone_number'],
                "age": user['age'],
                "height": user['height'],
                "weight": user['weight'],
                "gender": user['gender'],
                "health_goals": _decode(user['health_goals']),
                "preferred_diet_type": user['preferred_diet_type'],
                "preferred_cuisine": user['preferred_cuisine'],
                "allergies": _decode(user['allergies']),
                "health_conditions": _decode(user['health_conditions']),
                "activity_level": user['activity_level']
            }
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    def update_user_profile(self, user_id: int, updates: dict):
        """Update user profile information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build dynamic update query
            update_parts = []
            values = []
            
            for field, value in updates.items():
                if field in ['health_goals', 'allergies', 'health_conditions']:
                    # Convert lists to JSON strings
                    import json
                    update_parts.append(f"{field} = ?")
                    values.append(json.dumps(value) if value else None)
                else:
                    update_parts.append(f"{field} = ?")
                    values.append(value)
            
            if not update_parts:
                return False
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(update_parts)} WHERE id = ?"
            
            cursor.execute(query, values)
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False