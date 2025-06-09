import mysql.connector

connection = mysql.connector.connect(
    user="root",
    password="123456",
    host="localhost",
    database="znxz")

with connection.cursor() as cursor:
    # Example query to fetch all users
    cursor.execute("SELECT id FROM users WHERE email = %s",
                   ("488888888@qq.com", ))

    # Fetch all results
    results = cursor.fetchone()

    if results:
        user_id = results[0]
        print(f"User ID: {user_id}")
