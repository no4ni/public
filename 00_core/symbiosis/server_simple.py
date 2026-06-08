import http.server
import socketserver

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Сервер запущен: http://localhost:{PORT}")
    print(f"Для телефона: http://{ip_адрес_пк}:{PORT}")
    httpd.serve_forever()