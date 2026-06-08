# Создаем исправленный веб-сервер для Python 3.6
$fixedServerScript = @'
import http.server
import socketserver
import os
import urllib.parse
from datetime import datetime

PORT = 8000
BASE_DIR = "E:\\AGI\\symbiosis"

class FixedHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Преобразуем путь к файловой системе
        path = urllib.parse.unquote(path)
        
        # Если путь ведет к корню, возвращаем test_index.html
        if path == '/':
            path = '/test_index.html'
        
        # Убираем начальный слеш
        if path.startswith('/'):
            path = path[1:]
        
        # Возвращаем полный путь в нашей директории
        full_path = os.path.join(BASE_DIR, path)
        
        # Защита от directory traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(BASE_DIR)):
            return os.path.join(BASE_DIR, 'test_index.html')
        
        return full_path
    
    def do_GET(self):
        if self.path == '/config':
            self.send_config()
            return
        
        # Для всех остальных запросов используем стандартную логику
        super().do_GET()
    
    def send_config(self):
        try:
            config_path = os.path.join(BASE_DIR, "core", "body_config_pc.json")
            if os.path.exists(config_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Disposition', 'attachment; filename="body_config.json"')
                self.end_headers()
                with open(config_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Config file not found")
        except Exception as e:
            self.send_error(500, str(e))
    
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.client_address[0]} - {format % args}")

print(f"🚀 Исправленный веб-сервер для Python 3.6")
print(f"📁 Директория: {BASE_DIR}")
print(f"🌐 Порт: {PORT}")
print(f"⏱️  Время: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 50)

with socketserver.TCPServer(("", PORT), FixedHandler) as httpd:
    httpd.serve_forever()
'@

$fixedServerScript | Out-File -FilePath "E:\AGI\symbiosis\tools\fixed_server.py" -Encoding UTF8 -Force

Write-Host "✅ Исправленный сервер создан для Python 3.6" -ForegroundColor Green