import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, "lsp.py")


def send(proc, message):
    data = json.dumps(message).encode("utf-8")
    proc.stdin.write(f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8") + data)
    proc.stdin.flush()


def receive(proc):
    headers = {}
    while True:
        line = proc.stdout.readline().decode("utf-8").strip()
        if line == "":
            break
        key, value = line.split(":", 1)
        headers[key.lower()] = value.strip()
    length = int(headers["content-length"])
    return json.loads(proc.stdout.read(length).decode("utf-8"))


class TestLanguageServer(unittest.TestCase):
    def setUp(self):
        self.proc = subprocess.Popen(
            [sys.executable, SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    def tearDown(self):
        send(self.proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
        receive(self.proc)
        send(self.proc, {"jsonrpc": "2.0", "method": "exit"})
        self.proc.wait(timeout=5)

    def test_initialize(self):
        send(self.proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        response = receive(self.proc)
        self.assertEqual(response["result"]["capabilities"]["textDocumentSync"], 1)

    def test_diagnostics(self):
        send(self.proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        receive(self.proc)
        send(self.proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": "file:///test.sable", "text": 'let x: number = "a";'}},
        })
        notification = receive(self.proc)
        self.assertEqual(notification["method"], "textDocument/publishDiagnostics")
        diagnostics = notification["params"]["diagnostics"]
        self.assertTrue(diagnostics)
        self.assertIn("TypeError", diagnostics[0]["message"])


if __name__ == "__main__":
    unittest.main()
