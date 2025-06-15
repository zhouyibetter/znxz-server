import json
import re
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import asyncio

from prompt_toolkit.key_binding.bindings.named_commands import forward_word

from Dialog.models import *
from Utils.llm_api import StreamLlmApi
import httpx

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


async def forward_to_remote0(url: str, payload_name: str, question: str, session_id: int, extra_params: dict = None) -> \
AsyncGenerator[str, None]:
    """
    通用的远程请求转发函数，支持任何远程服务器URL
    """
    payload = {payload_name: question}
    if extra_params:
        payload.update(extra_params)

    yield f"# 正在连接到 {url}...\n"

    full_response = ""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream('POST', url, json=payload) as response:
                if response.status_code != 200:
                    error_msg = f"# ❌ 远程服务器返回错误状态码: {response.status_code}\n"
                    full_response += error_msg
                    yield error_msg
                    return

                yield "# ✅ 已连接，接收数据中...\n\n"

                async for chunk in response.aiter_text():
                    if chunk:
                        try:
                            # 尝试解析JSON
                            json_data = json.loads(chunk)

                            # 格式化JSON为更易读的文本
                            formatted_text = ""

                            # 如果是字典类型且有特定的键
                            if isinstance(json_data, dict):
                                if "review_result" in json_data:
                                    formatted_text = json_data["review_result"]
                                elif "generated_content" in json_data:
                                    formatted_text = json_data["generated_content"]
                                elif "error" in json_data:
                                    formatted_text = f"错误: {json_data['error']}"
                                else:
                                    # 将JSON转为格式化字符串
                                    formatted_text = json.dumps(json_data, ensure_ascii=False, indent=2)
                            else:
                                # 非字典类型，直接转换
                                formatted_text = json.dumps(json_data, ensure_ascii=False, indent=2)

                            full_response += formatted_text
                            yield formatted_text
                        except json.JSONDecodeError:
                            # 如果不是JSON，直接输出
                            full_response += chunk
                            yield chunk

                        await asyncio.sleep(0.01)
    except Exception as e:
        error_msg = f"# ❌ 远程请求失败: {str(e)}\n"
        full_response += error_msg
        yield error_msg

    # 保存完整响应到数据库
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO dialog (session_id, question, message) VALUES (%s, %s, %s)",
                           (session_id, question, full_response))
            connection.commit()
    except Exception as e:
        yield f"# ⚠️ 警告：无法保存对话记录: {str(e)}\n"


async def forward_to_remote(url: str, payload_name: str, question: str, session_id: int, extra_params: dict = None) -> AsyncGenerator[str, None]:
    """
    通用的远程请求转发函数，支持任何远程服务器URL
    """
    payload = {payload_name: question}
    if extra_params:
        payload.update(extra_params)

    yield f"# 正在连接到 {url}...\n"

    full_response = ""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream('POST', url, json=payload) as response:
                if response.status_code != 200:
                    error_msg = f"# ❌ 远程服务器返回错误状态码: {response.status_code}\n"
                    full_response += error_msg
                    yield error_msg
                    return

                yield "# ✅ 已连接，接收数据中...\n\n"

                async for chunk in response.aiter_text():
                    if chunk:
                        try:
                            # 尝试解析JSON
                            json_data = json.loads(chunk)

                            # 如果是执行结果，直接提取review_result
                            if "review_result" in json_data:
                                review_result = json_data["review_result"]
                                # 不再单独输出原始JSON，而是格式化后的内容
                                formatted_chunk = format_review_result(review_result)
                                full_response += formatted_chunk
                                yield formatted_chunk
                            # 如果是流式块，提取chunk字段
                            elif "chunk" in json_data:
                                chunk_content = json_data["chunk"]
                                full_response += chunk_content
                                yield chunk_content
                            # 其他情况，保持原样输出
                            else:
                                # 将JSON转换为可读格式
                                formatted_json = json.dumps(json_data, ensure_ascii=False, indent=2)
                                full_response += formatted_json
                                yield formatted_json
                        except json.JSONDecodeError:
                            # 如果不是JSON，直接输出
                            full_response += chunk
                            yield chunk

                        await asyncio.sleep(0.01)
    except Exception as e:
        error_msg = f"# ❌ 远程请求失败: {str(e)}\n"
        full_response += error_msg
        yield error_msg

    # 保存完整响应到数据库
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO dialog (session_id, question, message) VALUES (%s, %s, %s)",
                           (session_id, question, full_response))
            connection.commit()
    except Exception as e:
        yield f"# ⚠️ 警告：无法保存对话记录: {str(e)}\n"

# 添加一个新函数来格式化代码评审结果
def format_review_result(review_result: str) -> str:
    """
    格式化代码评审结果，将JSON转换为可读的格式
    """
    try:
        # 如果结果已经是JSON字符串，尝试解析它
        review_data = json.loads(review_result)

        # 格式化输出
        result = "# 代码评审结果\n\n"

        # 添加设计模式部分
        if "designPatterns" in review_data:
            result += "## 识别到的设计模式\n\n"
            patterns = review_data["designPatterns"]
            if not patterns:
                result += "未识别到任何设计模式\n\n"
            else:
                for pattern in patterns:
                    result += f"### {pattern['pattern']}\n"
                    result += f"**涉及类**: {', '.join(pattern['classes'])}\n"
                    result += f"**描述**: {pattern['description']}\n\n"

        # 添加设计问题部分
        if "designIssues" in review_data:
            result += "## 设计问题\n\n"
            issues = review_data["designIssues"]
            if not issues:
                result += "未发现设计问题\n\n"
            else:
                for issue in issues:
                    result += f"### {issue['issue']} (严重性: {issue['severity']})\n"
                    result += f"**涉及类**: {', '.join(issue['classes'])}\n"
                    result += f"**描述**: {issue['description']}\n\n"

        # 添加质量分数
        if "qualityScore" in review_data:
            result += f"## 代码质量评分\n\n**分数**: {review_data['qualityScore']}/100\n\n"

        # 添加建议
        if "suggestions" in review_data:
            result += "## 改进建议\n\n"
            for i, suggestion in enumerate(review_data["suggestions"], 1):
                result += f"{i}. {suggestion}\n"
            result += "\n"

        # 添加类图
        if "graphviz" in review_data and review_data["graphviz"]:
            result += "## 类图 (Graphviz DOT)\n\n"
            result += "```dot\n"
            result += review_data["graphviz"]
            result += "\n```\n\n"
            result += "_你可以在 [GraphvizOnline](https://dreampuf.github.io/GraphvizOnline/) 中可视化此类图_\n\n"

        return result
    except json.JSONDecodeError:
        # 如果不是JSON，返回原始内容
        return review_result
    except Exception as e:
        # 处理其他错误
        return f"格式化评审结果时出错: {str(e)}\n\n原始内容:\n{review_result}"


async def forward_test_request(url: str, test_params: dict, session_id: int) -> AsyncGenerator[str, None]:
    """
    转发测试用例生成请求的专用函数
    """
    yield f"# 正在连接到测试用例生成服务 {url}...\n"

    full_response = ""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream('POST', url, json=test_params) as response:
                if response.status_code != 200:
                    error_msg = f"# ❌ 测试用例生成服务返回错误状态码: {response.status_code}\n"
                    full_response += error_msg
                    yield error_msg
                    return

                yield "# ✅ 已连接，正在生成测试用例...\n\n"

                async for chunk in response.aiter_text():
                    if chunk:
                        try:
                            # 尝试解析JSON响应
                            json_data = json.loads(chunk)
                            # 格式化输出JSON响应
                            formatted_output = format_test_response(json_data)
                            full_response += formatted_output
                            yield formatted_output
                        except json.JSONDecodeError:
                            # 如果不是JSON，直接输出
                            full_response += chunk
                            yield chunk
                        await asyncio.sleep(0.01)
    except Exception as e:
        error_msg = f"# ❌ 测试用例生成请求失败: {str(e)}\n"
        full_response += error_msg
        yield error_msg

    # 保存完整响应到数据库
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO dialog (session_id, question, message) VALUES (%s, %s, %s)",
                           (session_id, json.dumps(test_params), full_response))
            connection.commit()
    except Exception as e:
        yield f"# ⚠️ 警告：无法保存测试用例记录: {str(e)}\n"


def format_test_response(json_data: dict) -> str:
    """格式化测试用例响应"""
    result = "# 测试用例生成结果\n\n"

    # 添加边界值
    if "boundaryValues" in json_data:
        result += "## 边界值\n\n"
        boundary_values = json_data["boundaryValues"]

        if boundary_values is None:
            result += "无边界值数据\n\n"
        elif isinstance(boundary_values, list):
            if all(isinstance(item, str) for item in boundary_values):
                # 如果只有参数名称
                result += "### 参数名称\n"
                for value in boundary_values:
                    result += f"- {value}\n"

                # 添加建议的测试值
                result += "\n### 建议的测试值\n"
                result += "对于整数参数，建议测试以下边界值：\n"
                result += "- 最小值 (Integer.MIN_VALUE)\n"
                result += "- 负值 (-1)\n"
                result += "- 零 (0)\n"
                result += "- 正值 (1)\n"
                result += "- 最大值 (Integer.MAX_VALUE)\n\n"
            else:
                for value in boundary_values:
                    result += f"- {value}\n"
        else:
            result += f"- {boundary_values}\n"
        result += "\n"

    # 添加JUnit模板
    if "junitTemplate" in json_data:
        result += "## JUnit测试模板\n\n"
        result += "```java\n"
        result += json_data["junitTemplate"]
        result += "\n```\n\n"

        # 添加完整的示例实现
        result += "## 完整实现示例\n\n"
        result += "```java\n"
        template = json_data["junitTemplate"]

        # 提取类名和方法名
        class_match = re.search(r'(\w+) instance = new (\w+)\(\);', template)
        if class_match:
            class_name = class_match.group(2)
            method_name = None
            method_match = re.search(r'void test(\w+)\(', template)
            if method_match:
                method_name = method_match.group(1).lower()

            if method_name == "add":
                complete_impl = template.replace("// 请在此处添加断言逻辑",
                                                "int expected = a + b;\n  int result = instance.add(a, b);\n  assertEquals(expected, result);")
                result += complete_impl
                result += "\n\n// 添加测试数据源\npublic static Stream<Arguments> addCases() {\n"
                result += "  return Stream.of(\n"
                result += "    Arguments.of(0, 0),      // 零值测试\n"
                result += "    Arguments.of(1, 1),      // 正值测试\n"
                result += "    Arguments.of(-1, -1),    // 负值测试\n"
                result += "    Arguments.of(Integer.MAX_VALUE, 1),  // 边界值测试\n"
                result += "    Arguments.of(Integer.MIN_VALUE, -1), // 边界值测试\n"
                result += "    Arguments.of(100, -100)  // 相反值测试\n"
                result += "  );\n}"

        result += "\n```\n"

        # 添加必要的import语句
        result += "\n## 所需的import语句\n\n"
        result += "```java\n"
        result += "import org.junit.jupiter.api.Test;\n"
        result += "import org.junit.jupiter.params.ParameterizedTest;\n"
        result += "import org.junit.jupiter.params.provider.MethodSource;\n"
        result += "import static org.junit.jupiter.api.Assertions.*;\n"
        result += "import java.util.stream.Stream;\n"
        result += "import org.junit.jupiter.params.provider.Arguments;\n"
        result += "```\n"

    return result

def extract_class_name(java_code: str) -> str:
    """从Java代码中提取类名"""
    match = re.search(r'class\s+(\w+)', java_code)
    return match.group(1) if match else "UnknownClass"

def extract_method_name(java_code: str) -> str:
    """从Java代码中提取方法名"""
    match = re.search(r'\b\w+\s+(\w+)\s*\(', java_code)
    return match.group(1) if match else "unknownMethod"

async def call_test_agent(code: str) -> dict:
    """调用测试用例智能体 (端口5000)"""
    try:
        # 从Java代码中提取类名和方法名
        class_name = extract_class_name(code)
        method_name = extract_method_name(code)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:5000/api/testgen/generate",
                json={
                    "javaCode": code,
                    "targetClass": class_name,
                    "methodName": method_name
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except httpx.RequestError as e:
        return {"error": f"请求错误: {str(e)}"}
    except Exception as e:
        return {"error": f"意外错误: {str(e)}"}

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

        if mode == "1":
            print("mode1")
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

        if mode == "2":
            print("mode2")
            return StreamingResponse(
                forward_to_remote0("http://24f2eeeb.r5.cpolar.top/ask","question", question, session_id),
                media_type="text/plain"
            )

        # 任务路由
        if mode == "3":  # 使用字符串匹配，便于扩展
            print("mode3")  
            return StreamingResponse(
                forward_to_remote0("http://5e74c8f1.r5.cpolar.top/generate","user_story", question, session_id),
                media_type="text/plain"
            )

        if mode == "4":
            print("mode4")
            # 获取Java相关参数
            java_code = question
            target_class = data.get("targetClass", "")
            method_name = data.get("methodName", "")

            if not java_code:
                raise HTTPException(status_code=400, detail="Java代码不能为空")

            # 如果未提供类名和方法名，尝试从代码中提取
            if not target_class:
                target_class = extract_class_name(java_code)
                print(target_class)
            if not method_name:
                method_name = extract_method_name(java_code)
                print(method_name)

            # 创建JSON格式的测试参数
            test_params = {
                "javaCode": java_code,
                "targetClass": target_class,
                "methodName": method_name
            }

            # 使用自定义forward_test函数处理测试用例生成请求
            return StreamingResponse(
                forward_test_request(
                    "http://40225c6d.r29.cpolar.top/api/testgen/generate",
                    test_params,
                    session_id
                ),
                media_type="text/plain"
            )

        if mode == "5":
            print("mode5")
            return StreamingResponse(
                forward_to_remote("http://7e7bb7a1.r29.cpolar.top/review", "code", question, session_id),
                media_type="text/plain"
            )

        if mode == "6":
            print("mode6")
            return StreamingResponse(
                forward_to_remote("http://3c90e78d.r29.cpolar.top/review", "code", question, session_id),
                media_type="text/plain"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn

    # Run fastapi app
    uvicorn.run(app, host="127.0.0.1", port=8000)
