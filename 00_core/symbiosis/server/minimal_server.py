import http.server
import socketserver
import json
import os
from datetime import datetime

PORT = 8002
CONFIG_FILE = "config.json"

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Убираем слеш в конце пути для сравнения
        path = self.path.rstrip('/')
        
        if path == '' or path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Сервер симбиоза</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Сервер симбиоза работает 🚀</h1>
    <p>Алиса + Джарвис1 + Пользователь</p>
    <div class="endpoint">
        <strong>GET /config</strong> - Конфигурация системы<br>
        <a href="/config">/config</a>
    </div>
    <div class="endpoint">
        <strong>GET /status</strong> - Статус сервера<br>
        <a href="/status">/status</a>
    </div>
    <div class="endpoint">
        <strong>Время:</strong> ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''
    </div>
</body>
</html>'''
            self.wfile.write(html.encode('utf-8'))
            
        elif path == '/config':
            if os.path.exists(CONFIG_FILE):
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.send_error(404, 'Config file not found. Create config.json first.')
                
        elif path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            status = {
                "server": "running",
                "port": PORT,
                "timestamp": datetime.now().isoformat(),
                "agents": {
                    "jarvis1": "researching_financial_lacunae",
                    "alice": "server_management",
                    "Пользователь": "hardware_integration_planning"
                },
                "system": {
                    "config_file_exists": os.path.exists(CONFIG_FILE),
                    "config_file_size": os.path.getsize(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0,
                    "python_version": os.sys.version
                },
                "project": "symbiosis",
                "version": "0.1.0"
            }
            self.wfile.write(json.dumps(status, ensure_ascii=False, indent=2).encode('utf-8'))
            
        else:
            self.send_error(404, 'Endpoint not found. Available: /, /config, /status')
    
    def log_message(self, format, *args):
        # Убираем стандартное логирование каждого запроса
        pass

if __name__ == '__main__':
    print(f"╔{'═'*60}╗")
    print(f"║{'СЕРВЕР СИМБИОЗА':^60}║")
    print(f"╠{'═'*60}╣")
    print(f"║ {'Порт:':<15} {PORT:<43} ║")
    print(f"║ {'Конфиг файл:':<15} {CONFIG_FILE:<43} ║")
    print(f"╠{'═'*60}╣")
    print(f"║ {'Доступные endpoints:':<58} ║")
    print(f"║ {'  • http://localhost:8002/':<58} ║")
    print(f"║ {'  • http://localhost:8002/config':<58} ║")
    print(f"║ {'  • http://localhost:8002/status':<58} ║")
    print(f"╠{'═'*60}╣")
    print(f"║ {'Для проверки:':<58} ║")
    print(f"║ {'  curl http://localhost:8002/config':<58} ║")
    print(f"║ {'  или открой в браузере':<58} ║")
    print(f"╚{'═'*60}╝")
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"\n✅ Сервер запущен на 0.0.0.0:{PORT}")
            print("🔄 Ожидание запросов... (Ctrl+C для остановки)")
            httpd.serve_forever()
    except OSError as e:
        print(f"\n❌ Ошибка запуска: {e}")
        print("Возможно порт 8002 уже занят.")
        print("Проверьте: netstat -ano | findstr :8002")
    except KeyboardInterrupt:
        print(f"\n⏹️  Сервер остановлен")
