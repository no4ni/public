import http.server
import socketserver
import os
import json

PORT = 8001
HOST = "0.0.0.0"

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>Сервер симбиоза</h1><p>Порт: ' + str(PORT).encode() + b'</p>')
            self.wfile.write(b'<p><a href="/config">Конфигурация тела</a></p>')
        elif self.path == '/config':
            config_path = "E:\\\\AGI\\\\symbiosis\\\\core\\\\body_config_pc.json"
            if os.path.exists(config_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with open(config_path, 'rb') as f:
                    self.wfile.write(f.read())
                print(f"[CONFIG] Отправлено на порту {PORT}")
            else:
                self.send_error(404, 'Config not found')
        else:
            self.send_error(404, 'Not found')
    
    def log_message(self, format, *args):
        pass

print(f"Сервер запущен на {HOST}:{PORT}")
print(f"Конфигурация: http://localhost:{PORT}/config")
print(f"Для телефона: http://192.168.0.10:{PORT}/config")

with socketserver.TCPServer((HOST, PORT), ConfigHandler) as httpd:
    httpd.serve_forever()
