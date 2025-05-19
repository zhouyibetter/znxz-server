import json

from openai import OpenAI
from cryptography.fernet import Fernet

api_key = b'gAAAAABoJXqyrhK0vAFN5BZ9u5Ra8za8nHQU6BW5AAq6JXzYiqhOkIHTyB22s5LAaW-O66DgkumpiJfDqAPVw2KSjZXITfFcTODtvqLGleuTXTPmvg9-TbcEpsRPNHAagLgIQhWisfGJ'
key = b'upe2l6UFonRu7qzhWWRfIeYSHJt25nS11o7arzDFlMs='
cipher = Fernet(key)

BASE_URL = 'https://api.deepseek.com'
MODEL = 'deepseek-chat'  # DeepSeek V3

dpv3_client = OpenAI(
    base_url=BASE_URL,
    api_key=cipher.decrypt(api_key).decode()
)

# prompt
SYS_ROLE = "你是大学软件工程课程助手"


class LlmApi:
    def znxz(self, msg: str):
        response = dpv3_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYS_ROLE},
                {"role": "user", "content": msg},
            ],
            stream=False
        )

        return response.choices[0].message.content


class StreamLlmApi:
    """"DeepSeek-V3 的流式输出API"""

    def znxz(self, msg: str):
        response = dpv3_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYS_ROLE},
                {"role": "user", "content": msg},
            ],
            max_tokens=1024,
            temperature=0.7,
            stream=True
        )

        # Generator to yield chunks of data
        def stream_response():
            for chunk in response:
                if chunk == "data: [DONE]":
                    break
                try:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content  # Yield content chunk by chunk
                except json.JSONDecodeError:
                    yield "\nError decoding chunk: " + chunk.id

        return stream_response()


if __name__ == '__main__':
    # model = LlmApi()
    model = StreamLlmApi()
    resp = model.znxz("你是什么模型？")
    # print(resp)
