import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

if __package__:
    from .llm_rag import ask_rag
else:
    from llm_rag import ask_rag

APP_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = APP_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

HOST = os.getenv("CHAT_HOST", "127.0.0.1")
PORT = int(os.getenv("CHAT_PORT", "8000"))

STATIC_FILES = {
    "/": ("frontend/index.html", "text/html; charset=utf-8"),
    "/index.html": ("frontend/index.html", "text/html; charset=utf-8"),
    "/app.js": ("frontend/app.js", "application/javascript; charset=utf-8"),
    "/styles.css": ("frontend/styles.css", "text/css; charset=utf-8"),
}


class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        file_info = STATIC_FILES.get(self.path)
        if not file_info:
            self.send_error(HTTPStatus.NOT_FOUND, "File tidak ditemukan.")
            return

        file_name, content_type = file_info
        file_path = APP_DIR / file_name
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Asset frontend tidak ditemukan.")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint tidak ditemukan.")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
            question = str(payload.get("message", "")).strip()
            response = ask_rag(question)
            self._send_json(HTTPStatus.OK, response.model_dump())
        except json.JSONDecodeError:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Body request harus berupa JSON yang valid."},
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Terjadi kesalahan saat memproses chat: {exc}"},
            )

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        response_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    print(f"Chat UI berjalan di http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
