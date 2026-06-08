import http.server
import socketserver
import os
import urllib.parse

PORT = 8000

# Устанавливаем рабочую директорию
os.chdir("E:\\AGI\\symbiosis")

print("=" * 60)
print("🚀 Symbiosis Web Server")
print("📁 Directory:", os.getcwd())
print("🌐 Port:", PORT)
print("📶 External: http://192.168.0.10:8000")
print("=" * 60)

class SymbiosisHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        # Если запрос конфигурации
        if self.path == '/config' or self.path == '/body_config.json':
            self.send_config()
            return
        
        # Если корневой запрос - показываем тестовую страницу
        if self.path == '/':
            self.path = '/test_index.html'
        
        # Обрабатываем как обычный файл
        return super().do_GET()
    
    def send_config(self):
        """Отправляет конфигурацию тела"""
        try:
            config_file = "core\\body_config_pc.json"
            if os.path.exists(config_file):
                with open(config_file, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Disposition', 'attachment; filename="body_config.json"')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                print(f"[CONFIG] Sent body_config.json ({len(content)} bytes)")
            else:
                self.send_error(404, "Config file not found")
                print("[ERROR] Config file not found")
                
        except Exception as e:
            self.send_error(500, str(e))
            print(f"[ERROR] {e}")
    
    def log_message(self, format, *args):
        """Кастомный лог"""
        client_ip = self.client_address[0]
        print(f"[{self.log_date_time_string()}] {client_ip} - {format % args}")

# Создаем тестовую страницу если её нет
if not os.path.exists("test_index.html"):
    test_html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>✅ Symbiosis Web Server</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background: #000; color: #0f0; }
        .container { max-width: 600px; margin: 0 auto; }
        .card { background: #111; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .btn { display: inline-block; padding: 10px 20px; background: #005500; 
               color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Symbiosis Web Server</h1>
        <div class="card">
            <h3>Подключение успешно!</h3>
            <p>Сервер работает корректно.</p>
            <p><strong>IP:</strong> 192.168.0.10</p>
            <p><strong>Порт:</strong> 8000</p>
            <p><strong>Время запуска:</strong> Сейчас</p>
        </div>
        <div class="card">
            <h3>📥 Доступные действия:</h3>
            <p><a class="btn" href="/config">Скачать конфигурацию тела</a></p>
            <p>Или используйте ссылку: <a href="/config">/config</a></p>
        </div>
        <div class="card">
            <h3>📱 Для телефона:</h3>
            <p>В Termux выполните:</p>
            <pre style="background:#222;padding:10px;border-radius:5px;">
curl -o ~/symbiosis/core/body_config.json http://192.168.0.10:8000/config</pre>
        </div>
    </div>
</body>
</html>'''
    
    with open("test_index.html", "w", encoding="utf-8") as f:
        f.write(test_html)
    print("[INFO] Created test_index.html")

# Запускаем сервер
try:
    with socketserver.TCPServer(("", PORT), SymbiosisHandler) as httpd:
        print(f"[SERVER] Starting on port {PORT}...")
        httpd.serve_forever()
except Exception as e:
    print(f"[ERROR] Server failed: {e}")
    input("Press Enter to exit...")
