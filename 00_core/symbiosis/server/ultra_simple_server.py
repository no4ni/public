import socket
import threading
import json
import os

PORT = 8002
CONFIG_FILE = "config.json"

def handle_client(client_socket):
    try:
        # Получаем запрос
        request = client_socket.recv(1024).decode('utf-8', errors='ignore')
        
        # Определяем, что запросили
        if "GET /config" in request:
            # Пытаемся прочитать конфиг
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_data = f.read()
                response = f"""HTTP/1.0 200 OK
Content-Type: application/json; charset=utf-8

{config_data}"""
            else:
                # Если конфига нет - отдаем минимальный JSON
                response = """HTTP/1.0 200 OK
Content-Type: application/json; charset=utf-8

{"server": "running", "message": "Config file not found, using default"}"""
        
        elif "GET /status" in request:
            response = """HTTP/1.0 200 OK
Content-Type: application/json; charset=utf-8

{"server": "running", "port": 8002, "status": "online"}"""
        
        elif "GET /" in request:
            response = """HTTP/1.0 200 OK
Content-Type: text/html; charset=utf-8

<h1>Symbiosis Server</h1>
<p>Server is running</p>
<p><a href="/config">/config</a> - configuration</p>
<p><a href="/status">/status</a> - status</p>"""
        
        else:
            response = """HTTP/1.0 404 Not Found
Content-Type: text/html; charset=utf-8

<h1>404 Not Found</h1>"""
        
        # Отправляем ответ
        client_socket.send(response.encode('utf-8'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def main():
    print("=" * 50)
    print("Starting Symbiosis Server")
    print(f"Port: {PORT}")
    print("=" * 50)
    
    # Создаем сокет
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Пробуем забиндить порт
        server.bind(("0.0.0.0", PORT))
        server.listen(5)
        print(f"✅ Server started successfully")
        print(f"   Open in browser: http://localhost:{PORT}")
        print(f"   Or check with: curl http://localhost:{PORT}/config")
        print("=" * 50)
        
        # Главный цикл
        while True:
            client, addr = server.accept()
            print(f"Connection from {addr[0]}:{addr[1]}")
            
            # Обрабатываем в отдельном потоке
            client_thread = threading.Thread(target=handle_client, args=(client,))
            client_thread.daemon = True
            client_thread.start()
            
    except OSError as e:
        print(f"❌ Failed to start server: {e}")
        print("   Port 8002 might be already in use.")
        print("   Try closing other applications using this port.")
        print("=" * 50)
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    finally:
        server.close()

if __name__ == "__main__":
    main()
