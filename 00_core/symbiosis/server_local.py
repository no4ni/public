# Файл: E:\AGI\symbiosis\server.py
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os

class SymbiosisHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            # Отдаёт текущий статус системы
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {
                "time": "12:15",
                "coffee_ban": True,
                "active_task": "Настройка сервера",
                "medical_protocol": "ремиссия"
            }
            self.wfile.write(json.dumps(status).encode())
        else:
            # Отдаёт файлы из папки symbiosis
            super().do_GET()

# Запуск на порту 8080, только для локальной сети
server = HTTPServer(('127.0.0.1', 8080), SymbiosisHandler)
print("Сервер симбиоза запущен: http://127.0.0.1:8080")
server.serve_forever()
