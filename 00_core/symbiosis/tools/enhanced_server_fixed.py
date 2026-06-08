import http.server
import socketserver
import json
import os
from datetime import datetime

PORT = 8002
HOST = "0.0.0.0"

class EnhancedHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # API для Джарвис1 - лакуны агентов
        if self.path == '/api/altron-lacunas':
            self.send_json_response({"status": "research_started", "researcher": "Jarvis1"})
        
        # API для Джарвис2 - статус инфраструктуры
        elif self.path == '/api/infrastructure-status':
            status = {
                "server": "running",
                "port": PORT,
                "clients_connected": 1,
                "jarvis1": "researching_agents",
                "jarvis2": "managing_infrastructure",
                "timestamp": str(datetime.now())
            }
            self.send_json_response(status)
        
        # Конфигурация тела
        elif self.path == '/config':
            config_path = r"E:\AGI\symbiosis\core\body_config_pc.json"
            if os.path.exists(config_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with open(config_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, 'Config not found')
        
        # Статус симбиоза
        elif self.path == '/status':
            status_path = r"E:\AGI\symbiosis\SYMBIOSIS_STATUS.json"
            if os.path.exists(status_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with open(status_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_json_response({"error": "Status file not found"})
        
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = '<h1>Сервер симбиоза (Джарвис1+Джарвис2)</h1><p>Порт: ' + str(PORT) + '</p>'
            self.wfile.write(html.encode('utf-8'))
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        # Логируем только важные события
        if any(x in args for x in ['/api/', '/config', '/status']):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {' '.join(args)}")

print(f"Улучшенный сервер запущен на {HOST}:{PORT}")
print("Доступные эндпоинты:")
print("  /config - конфигурация тела")
print("  /status - статус симбиоза")
print("  /api/infrastructure-status - статус инфраструктуры")
print("  /api/altron-lacunas - для Джарвис1")

with socketserver.TCPServer((HOST, PORT), EnhancedHandler) as httpd:
    httpd.serve_forever()
