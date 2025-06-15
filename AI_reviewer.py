import json

from flask import Flask, request, jsonify
import os
import time
from datetime import datetime
import logging
from cryptography.fernet import Fernet
try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False
    logging.warning("openai模块未安装，服务将以模拟模式运行")

# 在文件顶部的app初始化后添加
app = Flask(__name__)
app.json.ensure_ascii = False  # 添加这行配置



# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JavaCodeReviewService")

# 服务配置
API_KEY_CIPHERTEXT = b'gAAAAABoJXqyrhK0vAFN5BZ9u5Ra8za8nHQU6BW5AAq6JXzYiqhOkIHTyB22s5LAaW-O66DgkumpiJfDqAPVw2KSjZXITfFcTODtvqLGleuTXTPmvg9-TbcEpsRPNHAagLgIQhWisfGJ'
DECRYPTION_KEY = b'upe2l6UFonRu7qzhWWRfIeYSHJt25nS11o7arzDFlMs='
BASE_URL = 'https://api.deepseek.com'
MODEL_NAME = 'deepseek-chat'  # 使用 deepseek-chat 模型

def get_system_prompt():
    """返回代码评审系统提示词"""
    return """您是一个经验丰富的Java代码评审专家。请分析下面的Java代码并生成专业的评审报告，报告需要包含以下部分：

# 总体评价
- 简要总结代码质量
- 指出主要优点和关键问题

# 详细问题报告
使用表格格式列出所有发现的问题：
| 类别       | 行号 | 问题描述                                 | 严重性 (HIGH/MEDIUM/LOW) | 改进建议 |
|------------|------|-----------------------------------------|--------------------------|----------|
| 代码设计   | ...  | ...                                     | ...                      | ...      |
| 命名规范   | ...  | ...                                     | ...                      | ...      |
| ...        | ...  | ...                                     | ...                      | ...      |

# 重构建议
- 针对高严重性问题提供具体重构方案

# 最佳实践总结
- 列出3-5条适用于此代码的Java最佳实践

评审要点:
1. 类名使用大驼峰命名法(PascalCase)
2. 方法名/变量名使用小驼峰命名法(camelCase)
3. 方法长度超过20行需关注复杂度
4. 重复代码识别
5. 异常处理策略评估
6. 资源管理检查
7. 并发安全分析
8. NPE风险排查
9. SOLID原则应用情况
10. 代码注释质量评估
"""

def initialize_openai_client():
    """初始化并返回OpenAI客户端"""
    try:
        cipher = Fernet(DECRYPTION_KEY)
        api_key = cipher.decrypt(API_KEY_CIPHERTEXT).decode()
        
        return OpenAI(
            base_url=BASE_URL,
            api_key=api_key
        )
    except Exception as e:
        logger.error(f"API密钥初始化失败: {str(e)}")
        return None

# 初始化客户端
openai_client = None
if openai_available:
    openai_client = initialize_openai_client()
else:
    logger.warning("未检测到openai库，服务将以模拟模式运行")

@app.route('/review', methods=['POST'])
def review_java_code():
    """Java代码评审API端点"""
    start_time = time.time()
    
    # 获取请求数据
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({
            "status": "error",
            "message": "缺少 'code' 参数",
            "execution_time": time.time() - start_time
        }), 400
    
    java_code = data['code']
    stream = data.get('stream', False)
    
    # 模拟模式（当openai库不可用时）
    if not openai_available or not openai_client:
        execution_time = time.time() - start_time
        review_result = f"# Java代码评审模拟报告\n\n**代码摘要:**\n{java_code[:200]}...\n\n**备注:** 服务未正确初始化，请检查openai库安装和API配置"
        
        if stream:
            return jsonify({
                "status": "simulation",
                "review_result": review_result,
                "execution_time": execution_time
            })
        else:
            return jsonify({
                "status": "simulation",
                "review_result": review_result,
                "execution_time": execution_time
            })
    
    try:
        if stream:
            # 流式处理
            return stream_review(java_code, start_time)
        else:
            # 同步处理
            return sync_review(java_code, start_time)
    
    except Exception as e:
        logger.error(f"代码评审失败: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": f"处理失败: {str(e)}",
            "execution_time": time.time() - start_time
        }), 500

def sync_review(java_code, start_time):
    """处理同步代码评审"""
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": f"请评审以下Java代码：\n```java\n{java_code}\n```"}
    ]
    
    response = openai_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=2500,
        stream=False
    )
    
    # 处理响应
    execution_time = time.time() - start_time
    review_result = response.choices[0].message.content.strip()

    return jsonify({
        "status": "success",
        "model": MODEL_NAME,
        "review_result": review_result,
        "execution_time": execution_time
    })

def stream_review(java_code, start_time):
    """处理流式代码评审"""
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": f"请评审以下Java代码：\n```java\n{java_code}\n```"}
    ]

    # 调用流式API
    response_stream = openai_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=2500,
        stream=True
    )

    def generate():
        review_content = []
        # 发送流开始信号
        yield json.dumps({
            "status": "stream_started",
            "model": MODEL_NAME,
            "start_time": datetime.now().isoformat()
        }, ensure_ascii=False) + "\n"  # 添加ensure_ascii=False

        # 处理流式响应
        try:
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    review_content.append(content_chunk)
                    # 发送每个内容块
                    yield json.dumps({
                        "chunk": content_chunk
                    }, ensure_ascii=False) + "\n"  # 添加ensure_ascii=False
        except Exception as e:
            logger.error(f"流处理中断: {str(e)}")
            yield json.dumps({
                "status": "stream_error",
                "error": f"流处理中断: {str(e)}"
            }) + "\n"
            return
        
        # 发送最终结果
        execution_time = time.time() - start_time
        full_response = ''.join(review_content)
        yield json.dumps({
            "status": "completed",
            "full_result": full_response,
            "execution_time": execution_time
        }) + "\n"
    
    # 返回流式响应
    return app.response_class(generate(), mimetype='text/event-stream')

@app.route('/status', methods=['GET'])
def service_status():
    """服务健康检查端点"""
    status = "running" if openai_available and openai_client else "error"
    return jsonify({
        "status": status,
        "model": MODEL_NAME,
        "openai_available": openai_available,
        "client_initialized": bool(openai_client),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """服务首页"""
    return """
    <h1>Java代码评审服务</h1>
    <p>使用POST /review接口进行Java代码评审</p>
    <p>示例请求:</p>
    <pre>
    POST /review
    Content-Type: application/json
    
    {
        "code": "public class Test { public static void main(String[] args) { System.out.println(\"Hello\"); } }",
        "stream": false
    }
    </pre>
    <p><a href="/status">服务状态检查</a></p>
    """

if __name__ == '__main__':
    # 启动服务
    port = int(os.environ.get('PORT', 8002))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    
    print(f"启动Java代码评审服务 (端口: {port})")
    print(f"API端点: POST http://localhost:{port}/review")
    print(f"健康检查: GET http://localhost:{port}/status")
    print(f"服务首页: GET http://localhost:{port}/")
    
    # 如果在模拟模式下运行，提示用户
    if not openai_available:
        print("\n警告: openai库未安装，服务将以模拟模式运行!")
        print("请执行以下命令安装依赖: pip install openai cryptography")
    
    app.run(host='0.0.0.0', port=port, debug=debug)