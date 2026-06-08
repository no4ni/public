import requests
import json

url = "http://127.0.0.1:8080/completion"
data = {
    "prompt": "<|user|>\nПривет, Алиса. Как дела?\n<|assistant|>\n",
    "temperature": 0.8,
    "top_p": 0.9,
    "repeat_penalty": 1.15,
    "max_tokens": 150,
	"stop": ["\n"]
}
try:
    response = requests.post(url, json=data, timeout=30)
    print(response.json())
except Exception as e:
    print(f"Ошибка: {e}")