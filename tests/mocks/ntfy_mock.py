# A tiny stand-in for the ntfy.sh relay (POST a message, read it back as SSE or JSON). Port 9292. /_dump shows everything it saw.
import json, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
MSGS = {}   # topic -> list of dicts
LOCK = threading.Lock()
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Access-Control-Allow-Headers", "*"); self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.send_header("Content-Length", "0"); self.end_headers()
    def do_POST(self):
        topic = self.path.strip("/"); n = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(n).decode()
        assert len(body) <= 4096, "ntfy message limit"
        with LOCK: MSGS.setdefault(topic, []).append({"id": uuid.uuid4().hex[:10], "time": int(time.time()), "event": "message", "topic": topic, "message": body})
        out = b"{}"; self.send_response(200); self.cors(); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
    def do_GET(self):
        if self.path.startswith("/_dump"):
            out = json.dumps(MSGS).encode(); self.send_response(200); self.cors(); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out); return
        parts = self.path.split("?")[0].strip("/").split("/"); topic = parts[0]; kind = parts[1] if len(parts) > 1 else ""
        if kind == "sse":
            self.send_response(200); self.cors(); self.send_header("Content-Type", "text/event-stream"); self.send_header("Connection", "close"); self.end_headers()
            sent = 0
            try:
                while True:
                    with LOCK: lst = list(MSGS.get(topic, []))
                    for m in lst[sent:]:
                        self.wfile.write(("event: message\ndata: %s\n\n" % json.dumps(m)).encode()); self.wfile.flush()
                    sent = len(lst); time.sleep(0.2)
            except Exception: return
        with LOCK: lst = list(MSGS.get(topic, []))
        out = "\n".join(json.dumps(m) for m in lst).encode()
        self.send_response(200); self.cors(); self.send_header("Content-Type", "application/x-ndjson"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
ThreadingHTTPServer(("127.0.0.1", 9292), H).serve_forever()
