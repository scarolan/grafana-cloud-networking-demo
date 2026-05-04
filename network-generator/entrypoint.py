"""Cloud Run entrypoint: start HTTP server immediately, load generator in background."""
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

port = int(os.environ.get("PORT", "9090"))
_ready = threading.Event()
_error = None


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if _error:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {_error}\n".encode())
            return
        if not _ready.is_set():
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"# loading\n")
            return
        output = generate_latest()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(output)

    def log_message(self, format, *args):
        pass


def load_generator():
    global _error
    try:
        # Disable LokiHandler for Cloud Run by patching env before import
        # (LokiHandler checks GRAFANA_LOGS_URL; if empty, emit() is a no-op)
        saved_url = os.environ.pop("GRAFANA_LOGS_URL", "")

        import generator

        # Restore for direct Loki push
        if saved_url:
            os.environ["GRAFANA_LOGS_URL"] = saved_url
            generator.loki.url = saved_url
            username = os.environ.get("GRAFANA_LOGS_USERNAME", "")
            token = os.environ.get("GRAFANA_CLOUD_TOKEN", "")
            if username and token:
                import base64
                cred = base64.b64encode(f"{username}:{token}".encode()).decode()
                generator.loki.auth = f"Basic {cred}"

        generator.init_state()
        generator.set_device_info()

        update_thread = threading.Thread(target=generator.update_loop, daemon=True)
        update_thread.start()
        _ready.set()
    except Exception as e:
        _error = f"{type(e).__name__}: {e}"
        import traceback
        traceback.print_exc()


server = HTTPServer(("0.0.0.0", port), MetricsHandler)

loader = threading.Thread(target=load_generator, daemon=True)
loader.start()

server.serve_forever()
