import sqlite3
import logging
import os
from datetime import datetime
from threading import Lock
from config.settings import Settings

class DBManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            
            # Initialize attributes here (Singleton)
            cls._instance.settings = Settings()
            cls._instance.logger = logging.getLogger("DeepVision.DB")
            cls._instance.db_path = cls._instance.settings.db_path
            
            cls._instance.init_db()
        return cls._instance

    def __init__(self):
        # Attributes are already initialized in __new__
        pass

    def get_connection(self):
        """
        Returns a new connection to the database.
        Each thread should call this to get its own connection.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # In a real SQLCipher scenario, we would do:
        # conn.execute(f"PRAGMA key = '{self.settings.db_password}';")
        # For this prototype/environment where sqlcipher might not be fully verifiable,
        # we will simulate the standard sqlite3 behavior but keep the architecture ready.
        return conn

    def init_db(self):
        """
        Initializes the database schema.Thread-safe.
        """
        with self._lock:
            try:
                # Ensure data dir exists
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Users Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT DEFAULT 'operator',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Events Table (Logs/Alarms)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL, -- WARNING, ALARM
                        event_type TEXT NOT NULL, -- CELLPHONE, FATIGUE, ROI_INTRUSION
                        message TEXT,
                        evidence_path TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        acknowledged BOOLEAN DEFAULT 0
                    )
                ''')

                # Settings Table (Runtime persistence)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')

                # Cameras Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cameras (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                conn.close()
                self.logger.info("Database initialized successfully.")
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {e}")

    def log_event(self, level, event_type, message, evidence_path=None):
        """
        Thread-safe method to log an event.
        """
        with self._lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO events (level, event_type, message, evidence_path)
                    VALUES (?, ?, ?, ?)
                ''', (level, event_type, message, evidence_path))
                conn.commit()
                conn.close()
            except Exception as e:
                self.logger.error(f"Error logging event: {e}")

    def get_settings(self, key, default=None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else default
        except Exception as e:
            self.logger.error(f"Error getting setting {key}: {e}")
            return default

    def set_setting(self, key, value):
        with self._lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
                conn.commit()
                conn.close()
            except Exception as e:
                self.logger.error(f"Error setting setting {key}: {e}")

    # --- Camera Management ---
    def add_camera(self, name, url):
        with self._lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO cameras (name, url) VALUES (?, ?)', (name, url))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error adding camera: {e}")
                return False

    def get_cameras(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, url FROM cameras ORDER BY id ASC')
            results = cursor.fetchall()
            conn.close()
            return results # List of tuples (id, name, url)
        except Exception as e:
            self.logger.error(f"Error getting cameras: {e}")
            return []

    def delete_camera(self, camera_id):
        with self._lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cameras WHERE id = ?', (camera_id,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error deleting camera: {e}")
                return False
