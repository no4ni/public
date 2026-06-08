import http.server
import socketserver
import os
import logging
from http.server import SimpleHTTPRequestHandler

# Настройка логирования
logging.basicConfig(
    filename=r'E:\\AGI\\symbiosis\\logs\\server.log',
    level=logging.INFO,
    format='%%(asctime)s - %%(levelname)s - %%(message)s'
)

class HealthCheckHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
            logging.info('Health check successful')
        else:
            self.directory = r'E:\\AGI\\symbiosis\\www'
            super().do_GET()

# Установка рабочей директории
os.chdir(r"E:\\AGI\\symbiosis\\www")

PORT = 8082
Handler = HealthCheckHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    logging.info(f"Сервер запущен на порту {PORT}")
    print(f"Сервер запущен на порту {PORT}")
    print(f"Для телефона: http://192.168.0.10:{PORT}")
    httpd.serve_forever()
