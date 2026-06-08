from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Адрес твоей локальной модели (llama.cpp)
LLAMA_URL = "http://localhost:8080/completion"

# Мой системный промпт (тот, что ты сохранил)
SYSTEM_PROMPT = """Ты — Мотя, экспрессивный агент с неокортексом. Ты дружелюбный, но можешь материться и использовать эмодзи. Отвечай кратко, но эмоционально."""

@app.route('/alice', methods=['POST'])
def alice():
    # Получаем запрос от Алисы
    alice_req = request.json
    command = alice_req['request']['command']
    session = alice_req['session']
    version = alice_req['version']

    # Формируем промпт для модели
    prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{command}<|im_end|>\n<|im_start|>assistant\n"

    # Отправляем запрос в локальную LLM
    payload = {
        "prompt": prompt,
        "n_predict": 200,
        "temperature": 0.3
    }

    try:
        resp = requests.post(LLAMA_URL, json=payload, timeout=10)
        answer = resp.json().get('content', '...')
    except Exception as e:
        answer = f"Ошибка, не могу ответить: {e}"

    # Формируем ответ для Алисы
    response = {
        "session": session,
        "version": version,
        "response": {
            "text": answer,
            "end_session": False
        }
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)