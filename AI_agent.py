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

app = Flask(__name__)

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
    return """
你是一位资深软件架构师，专注于分析Java代码设计模式和质量评估。你需要：
1. 全面分析代码结构，识别设计模式（单例、工厂、观察者等）
2. 检测设计问题（上帝对象、高耦合、违反开闭原则等）
3. 评估设计质量并给出0-100分评分
4. 提供具体可行的改进建议
5. 生成Graphviz DOT格式的类图代码

请严格按照以下JSON格式输出结果：
{
  "designPatterns": [{
    "pattern": "模式名称",
    "classes": ["主类", "关联类"],
    "description": "模式功能描述"
  }],
  "designIssues": [{
    "issue": "问题类型",
    "classes": ["涉及类名"],
    "description": "问题描述",
    "severity": "low/medium/high"
  }],
  "graphviz": "digraph G { ... }",
  "qualityScore": 整数分数,
  "suggestions": ["建议1", "建议2"]
}

重要规则：
1. 不要包含任何Markdown语法
2. 不要添加任何额外解释文本
3. 仅返回有效的JSON对象
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
    
    # 创建流式响应生成器
    def generate():
        review_content = []
        # 发送流开始信号
        yield json.dumps({
            "status": "stream_started",
            "model": MODEL_NAME,
            "start_time": datetime.now().isoformat()
        }) + "\n"
        
        # 处理流式响应
        try:
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    review_content.append(content_chunk)
                    # 发送每个内容块
                    yield json.dumps({
                        "chunk": content_chunk
                    }) + "\n"
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