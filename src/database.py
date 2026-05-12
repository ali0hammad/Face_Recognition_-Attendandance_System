import sqlite3
import os
import json
import numpy as np

DB_FILE = "attendance_system.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Students Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            face_encoding TEXT NOT NULL
        )
    ''')

    # Attendance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (roll_no) REFERENCES students (roll_no)
        )
    ''')

    conn.commit()
    conn.close()

def add_student(roll_no, name, face_encoding):
    conn = get_connection()
    cursor = conn.cursor()

    # Convert numpy array to list, then to JSON string for storage
    encoding_str = json.dumps(face_encoding.tolist())

    try:
        cursor.execute('''
            INSERT INTO students (roll_no, name, face_encoding)
            VALUES (?, ?, ?)
        ''', (roll_no, name, encoding_str))
        conn.commit()
        return True, "Student registered successfully."
    except sqlite3.IntegrityError:
        return False, f"Student with Roll No {roll_no} already exists."
    finally:
        conn.close()

def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT roll_no, name, face_encoding FROM students')
    rows = cursor.fetchall()
    conn.close()

    students = []
    for row in rows:
        roll_no, name, encoding_str = row
        # Convert JSON string back to numpy array
        encoding = np.array(json.loads(encoding_str))
        students.append({
            'roll_no': roll_no,
            'name': name,
            'encoding': encoding
        })
    return students

def mark_attendance(roll_no, date, time, status):
    conn = get_connection()
    cursor = conn.cursor()

    # Check if already marked today
    cursor.execute('''
        SELECT * FROM attendance WHERE roll_no = ? AND date = ?
    ''', (roll_no, date))

    if cursor.fetchone():
        conn.close()
        return False, "Already Marked"

    cursor.execute('''
        INSERT INTO attendance (roll_no, date, time, status)
        VALUES (?, ?, ?, ?)
    ''', (roll_no, date, time, status))
    conn.commit()
    conn.close()
    return True, "Attendance Marked"

def get_attendance_logs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.roll_no, s.name, a.date, a.time, a.status
        FROM attendance a
        JOIN students s ON a.roll_no = s.roll_no
        ORDER BY a.date DESC, a.time DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_student(old_roll_no, new_roll_no, new_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Update student details
        cursor.execute('''
            UPDATE students SET roll_no = ?, name = ? WHERE roll_no = ?
        ''', (new_roll_no, new_name, old_roll_no))

        # Cascade update to attendance logs if roll number changed
        if old_roll_no != new_roll_no:
            cursor.execute('''
                UPDATE attendance SET roll_no = ? WHERE roll_no = ?
            ''', (new_roll_no, old_roll_no))

        conn.commit()
        return True, "Student updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Roll No {new_roll_no} is already taken."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def delete_student(roll_no):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM attendance WHERE roll_no = ?', (roll_no,))
        cursor.execute('DELETE FROM students WHERE roll_no = ?', (roll_no,))
        conn.commit()
        return True, "Student deleted successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
