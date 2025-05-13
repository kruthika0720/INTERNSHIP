import sqlite3
conn = sqlite3.connect("employees.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT
    )
''')
employees = [("TKM1001", "password123"), ("TKM1002", "mypassword"), ("TKM1003", "securepass")]
for emp in employees:
    try:
        cursor.execute("INSERT INTO employees (emp_id, password) VALUES (?, ?)", emp)
    except:
        pass  # Ignore duplicates
conn.commit()
conn.close()
print("Database created with employees!")