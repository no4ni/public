# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class ExecutingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_json(200, {"status": "ok", "port": 8003})
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        if self.path == '/command':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(post_data)
                
                command = data.get('command', '')
                cmd_id = data.get('id', '')
                
                print(f"[SERVER] Executing command: {command[:50]}...")
                
                # ВЫПОЛНЕНИЕ КОМАНДЫ В TERMUX (через subprocess)
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    executable='/data/data/com.termux/files/usr/bin/bash' if sys.platform != 'win32' else None
                )
                
                response = {
                    "id": cmd_id,
                    "status": "executed",
                    "returncode": result.returncode,
                    "stdout": result.stdout[:500],  # ограничиваем вывод
                    "stderr": result.stderr[:500]
                }
                
                self.send_json(200, response)
                
            except subprocess.TimeoutExpired:
                self.send_json(408, {"error": "Command timeout"})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
        else:
            self.send_error(404, "Not Found")
    
    def send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование
        pass

if __name__ == '__main__':
    server = HTTPServer(('', 8003), ExecutingHandler)
    print("Исполняющий сервер запущен на порту 8003")
    print("Локальный: http://localhost:8003")
    print("Сетевой: http://192.168.0.10:8003")
    print("Сервер выполняет команды...")
    server.serve_forever()
