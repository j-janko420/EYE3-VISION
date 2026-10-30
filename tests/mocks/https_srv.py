# Serves the repository over https on 127.0.0.1:8443 with a throw-away certificate (for the https-page tests).
import http.server, os, ssl
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
h = http.server.ThreadingHTTPServer(("127.0.0.1", 8443), http.server.SimpleHTTPRequestHandler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain("/tmp/eye3_cert.pem", "/tmp/eye3_key.pem")
h.socket = ctx.wrap_socket(h.socket, server_side=True)
h.serve_forever()
