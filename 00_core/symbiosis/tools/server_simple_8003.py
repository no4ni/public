# Simple symbiosis server for connection with Termux
# Port: 8003
# ASCII only to avoid encoding issues

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"status": "ok", "port": 8003})
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        if self.path == '/command':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({
                    "status": "received", 
                    "command": data.get('command', ''),
                    "id": data.get('id', '')
                })
                self.wfile.write(response.encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        else:
            self.send_error(404, "Not Found")

def run():
    server = HTTPServer(('', 8003), Handler)
    print("Server started on port 8003")
    print("Local: http://localhost:8003/")
    print("Network: http://192.168.0.10:8003/")
    server.serve_forever()

if __name__ == '__main__':
    run()