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


class LlmApi:
    def znxz(self, msg: str):
        response = dpv3_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是软件工程专家"},
                {"role": "user", "content": msg},
            ],
            stream=False
        )

        return response.choices[0].message.content


if __name__ == '__main__':
    model = LlmApi()
    resp = model.znxz("你是什么模型？")
    print(resp)
