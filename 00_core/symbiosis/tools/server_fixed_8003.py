import http.server
import socketserver
import os
import json

PORT = 8003
HOST = "0.0.0.0"

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # �������� ������
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f'''<html>
                <head><title>������ ��������</title></head>
                <body>
                    <h1>������ �������� ��������!</h1>
                    <p>����: {PORT}</p>
                    <p><a href="/config">������� ������������ ����</a></p>
                    <p>��� ��������: http://192.168.0.10:{PORT}/config</p>
                </body>
            </html>'''
            self.wfile.write(html.encode('utf-8'))
        
        # ������������
        elif self.path == '/config':
            config_path = r"E:\AGI\symbiosis\core\body_config_pc.json"
            if os.path.exists(config_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Disposition', 'attachment; filename="body_config.json"')
                self.end_headers()
                with open(config_path, 'rb') as f:
                    self.wfile.write(f.read())
                print(f"[{self.client_address[0]}] ������������ ����������")
            else:
                self.send_error(404, 'Config file not found')
                print("[ERROR] ���� ������������ �� ������")
        
        # ��� ���� ��������� �������� - 404
        else:
            self.send_error(404, 'Not Found')
    
    def log_message(self, format, *args):
        # ����������� �����������
        pass

# ������ �������
print(f"������ ������� �� {HOST}:{PORT}")
print(f"��������� ������: http://localhost:{PORT}/")
print(f"������� ������: http://192.168.0.10:{PORT}/")
print("��� ���������: Ctrl+C")

try:
    with socketserver.TCPServer((HOST, PORT), ConfigHandler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\n������ ����������")
except Exception as e:
    print(f"������: {e}")
