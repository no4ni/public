import http.server
import socketserver
import os
from datetime import datetime

PORT = 8000
BASE_DIR = "E:\\AGI\\symbiosis"

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            self.path = '/test_index.html'
        elif self.path == '/config':
            self.send_config()
            return
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

print(f"🚀 Простой веб-сервер запущен на порту {PORT}")
print(f"📁 Директория: {BASE_DIR}")
print(f"⏱️  Время: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 50)

with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
    httpd.serve_forever()
