import http.server
import socketserver
import json
import os
import logging
from http.server import SimpleHTTPRequestHandler

# Настройка логирования
logging.basicConfig(
    filename=r'E:\\AGI\\symbiosis\\logs\\server.log',
    level=logging.INFO,
    format='%%(asctime)s - %%(levelname)s - %%(message)s'
)

class ApiHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
            logging.info('Health check successful')
        elif self.path == '/api/state':
            try:
                with open(r'E:\\AGI\\symbiosis\\coordination\\state_index.json', 'r') as f:
                    state = json.load(f)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(state).encode('utf-8'))
            except Exception as e:
                logging.error(f'API error: {str(e)}')
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.directory = r'E:\\AGI\\symbiosis\\www'
            super().do_GET()

# Установка рабочей директории
os.chdir(r"E:\\AGI\\symbiosis")

PORT = 8082
Handler = ApiHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    logging.info(f"Сервер запущен на порту {PORT}")
    print(f"Сервер запущен на порту {PORT}")
    print(f"Для телефона: http://192.168.0.10:{PORT}")
    httpd.serve_forever()
