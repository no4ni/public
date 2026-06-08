#!/usr/bin/env python3
"""
Улучшенный API сервер Хеймдалля
Запускается на всех интерфейсах, с правильной обработкой CORS
"""

import json
import datetime
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket

class HeimdallAPIHandler(BaseHTTPRequestHandler):
    """Обработчик запросов API Хеймдалля"""
    
    def _set_headers(self, status=200, content_type='application/json'):
        """Устанавливает заголовки ответа"""
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        """Обработка CORS preflight запросов"""
        self._set_headers(200)
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/health':
            self._health_check()
        elif parsed_path.path == '/api/agents':
            self._list_agents()
        elif parsed_path.path == '/':
            self._serve_index()
        elif parsed_path.path == '/heimdall_monitor.html':
            self._serve_monitor()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def do_POST(self):
        """Обработка POST запросов"""
        if self.path == '/api/signal':
            self._receive_signal()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def _health_check(self):
        """Проверка здоровья сервера"""
        self._set_headers(200)
        response = {
            'status': 'OK',
            'service': 'heimdall_coordination_api',
            'timestamp': datetime.datetime.now().isoformat(),
            'endpoints': {
                'health': '/health',
                'agents': '/api/agents',
                'signal': '/api/signal (POST)',
                'monitor': '/heimdall_monitor.html'
            }
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def _list_agents(self):
        """Возвращает список агентов"""
        agents = []
        try:
            agi_dir = "E:/AGI"
            for file in os.listdir(agi_dir):
                if file.endswith('.txt') and not file.startswith('_'):
                    filepath = os.path.join(agi_dir, file)
                    stats = os.stat(filepath)
                    agents.append({
                        'name': file.replace('.txt', ''),
                        'file': file,
                        'size': stats.st_size,
                        'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        'type': 'agent_file'
                    })
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        
        self._set_headers(200)
        response = {
            'count': len(agents),
            'agents': agents[:20],  # первые 20
            'total_in_system': len([f for f in os.listdir(agi_dir) if f.endswith('.txt')])
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def _receive_signal(self):
        """Принимает сигнал от агента"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': 'Empty request'}).encode())
            return
        
        try:
            post_data = self.rfile.read(content_length)
            signal_data = json.loads(post_data.decode('utf-8'))
            
            # Сохраняем сигнал
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            signal_file = f"E:/AGI/coordination/signals/received_{timestamp}.json"
            
            full_signal = {
                **signal_data,
                'received_at': datetime.datetime.now().isoformat(),
                'received_by': 'heimdall_api',
                'client_ip': self.client_address[0],
                'signal_file': signal_file
            }
            
            # Создаем директорию если нет
            os.makedirs(os.path.dirname(signal_file), exist_ok=True)
            
            with open(signal_file, 'w', encoding='utf-8') as f:
                json.dump(full_signal, f, ensure_ascii=False, indent=2)
            
            self._set_headers(201)
            response = {
                'status': 'Signal stored',
                'file': signal_file,
                'timestamp': full_signal['received_at']
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _serve_index(self):
        """Отдает простую HTML страницу"""
        self._set_headers(200, 'text/html')
        html = f'''
        <!DOCTYPE html>
        <html>
        <head><title>Хеймдалль API</title></head>
        <body>
            <h1>🛡️ Хеймдалль - API координации</h1>
            <p>API сервер активен. Доступные endpoints:</p>
            <ul>
                <li><a href="/health">/health</a> - Проверка здоровья</li>
                <li><a href="/api/agents">/api/agents</a> - Список агентов</li>
                <li><a href="/heimdall_monitor.html">/heimdall_monitor.html</a> - Веб-монитор</li>
            </ul>
            <p>Локальный IP: {socket.gethostbyname(socket.gethostname())}</p>
            <p>Время: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </body>
        </html>
        '''
        self.wfile.write(html.encode())
    
    def _serve_monitor(self):
        """Отдает страницу мониторинга"""
        monitor_path = "E:/AGI/symbiosis/www/heimdall_monitor.html"
        if os.path.exists(monitor_path):
            self._set_headers(200, 'text/html')
            with open(monitor_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Monitor page not found'}).encode())
    
    def log_message(self, format, *args):
        """Кастомное логирование"""
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {args[0]} {args[1]} {args[2]}")

def run_server(port=8083, host='0.0.0.0'):
    """Запускает сервер"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, HeimdallAPIHandler)
    
    print(f"✅ Хеймдалль API сервер запущен")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Local: http://127.0.0.1:{port}")
    print(f"   Network: http://{socket.gethostbyname(socket.gethostname())}:{port}")
    print(f"   Endpoints:")
    print(f"     • /health - проверка здоровья")
    print(f"     • /api/agents - список агентов")
    print(f"     • /heimdall_monitor.html - веб-монитор")
    print(f"   Нажмите Ctrl+C для остановки")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️ Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    port = 8083
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Использую порт по умолчанию: {port}")
    
    run_server(port)
