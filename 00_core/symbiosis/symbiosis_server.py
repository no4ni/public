import http.server
import socketserver
import os

PORT = 8000
DIR = "E:/AGI/symbiosis"

class SymbiosisHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)
    
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "active", "project": "symbiosis"}')
        else:
            super().do_GET()

with socketserver.TCPServer(("0.0.0.0", PORT), SymbiosisHandler) as httpd:
    print(f"✅ Сервер симбиоза запущен: http://localhost:{PORT}")
    print(f"📱 Для телефона: http://192.168.0.10:{PORT}")
    httpd.serve_forever()
