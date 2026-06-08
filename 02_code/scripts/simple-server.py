import http.server
import socketserver
import socket
import sys
import os   # ← вот этот импорт был пропущен

def get_local_ip():
    """Возвращает локальный IPv4-адрес, не 127.0.0.1"""
    try:
        # Подключаемся к внешнему DNS, чтобы узнать реальный интерфейс
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # fallback: берём первый не-loopback адрес
        ip = socket.gethostbyname_ex(socket.gethostname())[2][0]
        return ip

PORT = 8082
if len(sys.argv) > 1:
    PORT = int(sys.argv[1])

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("Сервер запущен на порту {}".format(PORT))
    print("Локальный доступ: http://localhost:{}".format(PORT))
    print("Для телефона: http://{}:{}".format(get_local_ip(), PORT))
    print("Текущая папка: {}".format(os.getcwd()))
    httpd.serve_forever()