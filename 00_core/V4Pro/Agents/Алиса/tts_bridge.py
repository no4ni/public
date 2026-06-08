#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from flask import Flask, request, jsonify

# ===== НАСТРОЙКИ (измени под себя) =====
OPENHAB_URL = "http://localhost:8081"          # адрес openHAB
OPENHAB_ITEM = "YandexStation_Say"             # имя item для TTS
OPENHAB_USER = None                             # если openHAB требует логин
OPENHAB_PASS = None                              # и пароль
# =========================================

app = Flask(__name__)

@app.route('/tts', methods=['POST'])
def tts():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' in JSON"}), 400

    text = data['text']
    headers = {'Content-Type': 'text/plain; charset=utf-8'}
    auth = (OPENHAB_USER, OPENHAB_PASS) if OPENHAB_USER and OPENHAB_PASS else None

    try:
        r = requests.post(
            f"{OPENHAB_URL}/rest/items/{OPENHAB_ITEM}",
            data=text.encode('utf-8'),
            headers=headers,
            auth=auth,
            timeout=10
        )
        if r.status_code in (200, 201, 202):
            return jsonify({"status": "ok", "openhab_status": r.status_code})
        else:
            return jsonify({
                "error": f"openHAB returned {r.status_code}",
                "details": r.text
            }), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=False)