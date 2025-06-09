from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from User.models import *
import mysql.connector

app = FastAPI()

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://zhouyibetter.tech:5173",
        "http://localhost:5173",
        "http://49bdef0.r24.cpolar.top",  # 显式添加后端域名
        "https://49bdef0.r24.cpolar.top",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connection = mysql.connector.connect(
    user="root",
    password="123456",
    host="localhost",
    database="user_znxz")


@app.post("/register")
async def register_user(info: RegisterInfo):
    """
    Register a new user.
    """
    email = info.email
    password = info.password

    with connection.cursor() as cursor:
        token = ""
        # Check if the user already exists
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))

        if cursor.fetchone():
            # User already exists
            return Result(code=2, token=token)

        # Insert the new user into the database
        try:
            cursor.execute(
                "INSERT INTO user (email, password) VALUES (%s, %s)", (email, password))
            connection.commit()

            # JWT token generation would go here
            # For simplicity, we are returning an self-design token
            cursor.execute(
                "SELECT id FROM user WHERE email = %s", (email,))

            result = cursor.fetchone()

            if result is not None:
                user_id = result[0]
                token = str(user_id)  # Simple token for demonstration
            return Result(code=0, token=token)
        except mysql.connector.Error as err:
            connection.rollback()
            return Result(code=1, token=token)


@app.post("/login")
async def login_user(info: LoginInfo):
    """
    Log in an existing user.
    """
    email = info.email
    password = info.password
    print(email, password)

    with connection.cursor() as cursor:
        token = ""
        # Check if the user exists and the password matches
        cursor.execute(
            "SELECT id FROM user WHERE email = %s AND password = %s", (email, password))

        result = cursor.fetchone()

        if result:
            user_id = result[0]
            # JWT token generation would go here
            token = str(user_id)
            return Result(code=0, token=token)
        else:
            return Result(code=1, token=token)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
