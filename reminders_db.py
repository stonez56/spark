import sqlite3
import os

DB_PATH = 'reminders.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Drop old table if it exists (since we're fundamentally changing schema)
    # Be careful in production, but for local dev this is fine.
    try:
        c.execute('SELECT times FROM reminders LIMIT 1')
    except sqlite3.OperationalError:
        # If 'times' column doesn't exist, we assume it's the old schema and drop it.
        c.execute('DROP TABLE IF EXISTS reminders')
        
    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            times TEXT NOT NULL,
            days_of_week TEXT DEFAULT '0,1,2,3,4,5,6',
            start_date TEXT,
            end_date TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def get_all_reminders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, message, times, days_of_week, start_date, end_date, is_active FROM reminders')
    rows = c.fetchall()
    conn.close()
    return [{
        "id": r[0], 
        "message": r[1], 
        "times": r[2], 
        "days_of_week": r[3],
        "start_date": r[4],
        "end_date": r[5],
        "is_active": bool(r[6])
    } for r in rows]

def add_reminder(message, times, days_of_week='0,1,2,3,4,5,6', start_date=None, end_date=None, is_active=True):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO reminders (message, times, days_of_week, start_date, end_date, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (message, times, days_of_week, start_date, end_date, int(is_active)))
    conn.commit()
    conn.close()

def update_reminder(reminder_id, message, times, days_of_week, start_date, end_date, is_active):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE reminders 
        SET message=?, times=?, days_of_week=?, start_date=?, end_date=?, is_active=?
        WHERE id=?
    ''', (message, times, days_of_week, start_date, end_date, int(is_active), reminder_id))
    conn.commit()
    conn.close()

def delete_reminder(reminder_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM reminders WHERE id=?', (reminder_id,))
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
