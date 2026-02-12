import http.server
import socketserver
import os

PORT = 8000
DATA_FILE = "data.json"

class MockRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f"Received GET request: {self.path}")

        if not os.path.exists(DATA_FILE):
            self.send_error(404, f"File {DATA_FILE} not found")
            return

        try:
            # 1. Read file in BINARY mode ("rb") to get exact byte count
            with open(DATA_FILE, "rb") as f:
                data = f.read()
            
            # 2. Send headers
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()

            # 3. Send binary data directly
            self.wfile.write(data)
            self.wfile.flush() # Force send
            
        except Exception as e:
            print(f"Error: {e}")
            # Only try to send error if headers haven't been sent
            try:
                self.send_error(500, str(e))
            except:
                pass

# Enable address reuse to prevent "Address already in use" errors on restart
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("0.0.0.0", PORT), MockRequestHandler) as httpd:
    print(f"Serving '{DATA_FILE}' on port {PORT} (IPv4)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")