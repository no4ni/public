import json
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import traceback

class FixedHandler(BaseHTTPRequestHandler):
    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, {"status": "ok", "server": "fixed"})
        else:
            self._send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        if self.path == '/command':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(post_data)
                
                command = data.get('command', '')
                cmd_id = data.get('id', 'unknown')
                
                print(f"[SERVER] Command received: {cmd_id}")
                print(f"[SERVER] Command: {command}")
                
                # ИСПРАВЛЕНИЕ: замена text=True на universal_newlines=True для Python 3.6
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    universal_newlines=True,  # вместо text=True
                    timeout=15
                )
                
                response = {
                    "id": cmd_id,
                    "status": "executed",
                    "returncode": result.returncode,
                    "stdout": result.stdout[:1000],
                    "stderr": result.stderr[:1000]
                }
                
                self._send_json(200, response)
                
            except subprocess.TimeoutExpired:
                self._send_json(408, {"error": "Timeout", "id": cmd_id})
            except Exception as e:
                error_trace = traceback.format_exc()
                print(f"[SERVER ERROR]: {error_trace}")
                self._send_json(500, {"error": str(e), "trace": error_trace})
        else:
            self._send_json(404, {"error": "Not found"})
    
    def log_message(self, format, *args):
        pass

def run():
    port = 8003
    server = HTTPServer(('', port), FixedHandler)
    print(f"[SERVER] Fixed server started on port {port}")
    print(f"[SERVER] Using universal_newlines=True for Python 3.6")
    server.serve_forever()

if __name__ == '__main__':
    run()
