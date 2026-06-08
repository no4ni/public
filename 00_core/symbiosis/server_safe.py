import sys
import socket
import http.server
import socketserver

PORT = 8082
try:
    # Проверяем, доступен ли порт
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', PORT))
    sock.close()
    
    if result == 0:
        print(f"Порт {PORT} уже занят. Попробуйте другой порт.")
        sys.exit(1)
        
    # Запускаем сервер
    with socketserver.TCPServer(("0.0.0.0", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        print(f"✅ Сервер запущен на порту {PORT}")
        print(f"📱 Для телефона: http://192.168.0.10:{PORT}")
        print(f"📁 Текущая папка: E:\AGI\symbiosis")
        httpd.serve_forever()
except OSError as e:
    print(f"Ошибка: {e}")
    if e.errno == 10048:
        print("Порт занят. Завершите процессы на этом порту.")
    elif e.errno == 13:
        print("Недостаточно прав. Запустите от администратора.")