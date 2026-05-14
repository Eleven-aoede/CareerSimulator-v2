import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.xi-ai.cn/v1",
    api_key=os.environ.get("XI_API_KEY")
)

resp = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[{"role": "user", "content": "你好！"}]
)
print(resp.choices[0].message.content)