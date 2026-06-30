import sqlite3
import datetime

conn = sqlite3.connect('f:/FlexTime/data/flextime.db')
c = conn.cursor()

c.execute("SELECT id FROM leave_types WHERE code = 'DAY_OFF'")
if not c.fetchone():
    now = datetime.datetime.now().isoformat()
    c.execute("""
        INSERT INTO leave_types 
        (name, code, colour, contributes_hours, default_hours, is_system, is_active, sort_order, created_at, updated_at) 
        VALUES ('Day Off', 'DAY_OFF', '#94A3B8', 0, 0.0, 1, 1, 9, ?, ?)
    """, (now, now))
    conn.commit()
    print('Inserted Day Off')
else:
    print('Already exists')
