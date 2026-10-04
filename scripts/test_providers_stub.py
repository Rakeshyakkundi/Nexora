"""Exercises the real provider HTTP code path (request building + response
parsing) against a local stub server, without needing real API keys. Proves
the live path works before a real key ever arrives.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, ".")


class StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        if self.path.endswith("/chat/completions"):
            assert self.headers.get("Authorization") == "Bearer dummy-key", "missing/incorrect Bearer auth"
            assert body["messages"][0]["role"] == "system"
            payload = {"choices": [{"message": {"content": "OPENAI_COMPAT_OK"}}]}
        elif self.path.endswith("/v1/messages"):
            assert self.headers.get("x-api-key") == "dummy-key", "missing/incorrect x-api-key"
            assert self.headers.get("anthropic-version"), "missing anthropic-version header"
            assert isinstance(body["system"], str), "system must be a top-level string, not a message"
            # Include a non-text block to prove the parser doesn't assume content[0] is text.
            payload = {
                "content": [
                    {"type": "thinking", "thinking": "reasoning..."},
                    {"type": "text", "text": "ANTHROPIC_OK"},
                ]
            }
        else:
            self.send_response(404)
            self.end_headers()
            return

        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def check(label: str, condition: bool) -> None:
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), StubHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    import os

    os.environ["GROK_API_KEY"] = "dummy-key"
    os.environ["GROK_BASE_URL"] = f"http://127.0.0.1:{port}"
    os.environ["OPENAI_API_KEY"] = "dummy-key"
    os.environ["OPENAI_BASE_URL"] = f"http://127.0.0.1:{port}"
    os.environ["ANTHROPIC_API_KEY"] = "dummy-key"
    os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}"

    from backend.llm.providers import OpenAICompatProvider, AnthropicProvider

    openai_like = OpenAICompatProvider("grok", f"http://127.0.0.1:{port}", "grok-4", "dummy-key")
    check("openai-compat provider available", openai_like.available())
    text = openai_like.complete("sys", "user", 0.2)
    check("openai-compat provider parses response", text == "OPENAI_COMPAT_OK")

    anthropic = AnthropicProvider("anthropic", f"http://127.0.0.1:{port}", "claude-sonnet-5", "dummy-key")
    text = anthropic.complete("sys", "user", 0.2)
    check("anthropic provider skips non-text blocks and parses text", text == "ANTHROPIC_OK")

    server.shutdown()
    print("\nAll provider wire-format checks passed against the stub server.")


if __name__ == "__main__":
    main()
