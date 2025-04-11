import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="concisely"
    )
    print("✅ Connected to MySQL")
    conn.close()
except mysql.connector.Error as err:
    print(f"❌ Database Connection Error: {err}")
