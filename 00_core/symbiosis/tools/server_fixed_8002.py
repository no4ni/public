import http.server
import socketserver
import os
import json

PORT = 8002
HOST = "0.0.0.0"

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Корневой запрос
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f'''<html>
                <head><title>Сервер симбиоза</title></head>
                <body>
                    <h1>Сервер симбиоза работает!</h1>
                    <p>Порт: {PORT}</p>
                    <p><a href="/config">Скачать конфигурацию тела</a></p>
                    <p>Для телефона: http://192.168.0.10:{PORT}/config</p>
                </body>
            </html>'''
            self.wfile.write(html.encode('utf-8'))
        
        # Конфигурация
        elif self.path == '/config':
            config_path = r"E:\AGI\symbiosis\core\body_config_pc.json"
            if os.path.exists(config_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Disposition', 'attachment; filename="body_config.json"')
                self.end_headers()
                with open(config_path, 'rb') as f:
                    self.wfile.write(f.read())
                print(f"[{self.client_address[0]}] Конфигурация отправлена")
            else:
                self.send_error(404, 'Config file not found')
                print("[ERROR] Файл конфигурации не найден")
        
        # Для всех остальных запросов - 404
        else:
            self.send_error(404, 'Not Found')
    
    def log_message(self, format, *args):
        # Минимальное логирование
        pass

# Запуск сервера
print(f"Запуск сервера на {HOST}:{PORT}")
print(f"Локальный доступ: http://localhost:{PORT}/")
print(f"Сетевой доступ: http://192.168.0.10:{PORT}/")
print("Для остановки: Ctrl+C")

try:
    with socketserver.TCPServer((HOST, PORT), ConfigHandler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\nСервер остановлен")
except Exception as e:
    print(f"Ошибка: {e}")
