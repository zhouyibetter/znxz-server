from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import asyncio
from Dialog.models import *
from Utils.llm_api import StreamLlmApi

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

# 数据库连接配置
connection = mysql.connector.connect(
    user="root",
    password="123456",
    host="localhost",
    database="dialog_znxz")

model = StreamLlmApi()

async def verify_token(request: Request):
    """
    Verify the JWT token from the request headers.
    """
    authorization = request.headers.get("Authorization")  # 从 Header 中提取字段
    if authorization is None or authorization == "":
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/session_history",
         dependencies=[Depends(verify_token)])
async def get_session_history(request: Request):
    """
    Retrieve the session history.
    """
    # 这里可以使用验证后的 Request 对象
    authorization = request.headers.get("Authorization")

    try:
        user_id = int(authorization)  # type: ignore

        with connection.cursor() as cursor:
            # 查询用户的对话历史
            cursor.execute(
                "SELECT id, session_name FROM session WHERE user_id = %s ORDER BY created_at", (user_id,))
            results = cursor.fetchall()

            session_history = []
            if not results:
                return Result(type=1, message="No Session history found", session_history=[])

            # 将查询结果转换为字典列表
            for row in results:
                session_history.append(
                    # type: ignore
                    # type: ignore
                    Session(session_id=row[0], session_name=row[1]))

            return Result(type=1, message="Dialog history retrieved successfully", session_history=session_history)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")


@app.get("/dialog_history/{session_id}",
         dependencies=[Depends(verify_token)])
async def get_dialog_history(session_id: int):
    """
    Retrieve the dialog history for a specific session.
    """
    try:
        with connection.cursor() as cursor:
            # 查询指定会话的对话历史
            cursor.execute(
                "SELECT id, question, message FROM dialog WHERE session_id = %s ORDER BY created_at", (session_id,))
            results = cursor.fetchall()

            dialog_history = []
            if not results:
                return Result(type=2, message="No Dialog history found", dialog_history=[])

            # 将查询结果转换为字典列表
            for row in results:
                dialog_history.append(
                    Dialog(dialog_id=row[0], question=row[1], dialog_content=row[2]))

            return Result(type=2, message="Dialog history retrieved successfully", dialog_history=dialog_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dialog",
          dependencies=[Depends(verify_token)])
async def ask(request: Request):
    """
    Handle a dialog request.
    """
    try:
        authorization = request.headers.get("Authorization")
        user_id = int(authorization)  # type: ignore

        data = await request.json()

        mode = data.get("mode")
        question = data.get("question")
        if not question:
            raise HTTPException(
                status_code=400, detail="question cannot be null")
        
        session_id = data.get("session_id")

        if session_id == -1:
            # 获取数据库中最大的 session_id
            max_session_id = 0
            with connection.cursor() as cursor:
                cursor.execute("SELECT MAX(id) FROM session")
                max_session_id = cursor.fetchone()[0] or 0
            session_id = max_session_id + 1  # type: ignore

            session_name = question[:10] if len(question) > 10 else question
            # 插入新的会话记录
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO session (id, session_name, user_id) VALUES (%s, %s, %s)",
                    (session_id, session_name, user_id))
                connection.commit()

        # 任务路由
        if mode == 4:
            # 调用代码测试模块
            # 1. 输入检测

            # 2. 穿透访问

            # 3. response
            pass



        # 调用 LLM API 获取回答
        stream_generator = model.znxz(question)
        full_response = ""

        async def event_generator():
            nonlocal full_response
            for chunk in stream_generator:
                full_response += chunk
                yield chunk
                # 添加短暂等待让事件循环有机会处理其他任务
                await asyncio.sleep(0.01)

            # 传输完毕后存入对话历史
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO dialog (session_id, question, message) VALUES (%s, %s, %s)",
                               (session_id, question, full_response))
                connection.commit()

        # Use StreamingResponse to stream the output to the client
        return StreamingResponse(event_generator(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn

    # Run fastapi app
    uvicorn.run(app, host="127.0.0.1", port=8000)
