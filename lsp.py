#!/usr/bin/env python3
"""Minimal language server for Sable (diagnostics only)."""

import json
import sys

import sable


documents = {}


def send(payload):
    data = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
    sys.stdout.buffer.write(header + data)
    sys.stdout.buffer.flush()


def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.decode("utf-8").strip()
        if line == "":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length == 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def diagnostics(text):
    try:
        program = sable.parse(text)
        sable.Checker().check(program)
        return []
    except sable.SableError as error:
        line = max(0, error.line - 1)
        column = max(0, error.col - 1)
        return [{
            "range": {
                "start": {"line": line, "character": column},
                "end": {"line": line, "character": column + 1},
            },
            "severity": 1,
            "source": "sable",
            "message": f"{error.kind}: {error.message}",
        }]


def publish(uri):
    send({
        "jsonrpc": "2.0",
        "method": "textDocument/publishDiagnostics",
        "params": {"uri": uri, "diagnostics": diagnostics(documents.get(uri, ""))},
    })


def main():
    while True:
        message = read_message()
        if message is None:
            break
        method = message.get("method")
        params = message.get("params", {})
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": message["id"], "result": {
                "capabilities": {"textDocumentSync": 1}
            }})
        elif method == "initialized":
            pass
        elif method == "textDocument/didOpen":
            document = params["textDocument"]
            documents[document["uri"]] = document["text"]
            publish(document["uri"])
        elif method == "textDocument/didChange":
            uri = params["textDocument"]["uri"]
            documents[uri] = params["contentChanges"][-1]["text"]
            publish(uri)
        elif method == "textDocument/didSave":
            publish(params["textDocument"]["uri"])
        elif method == "shutdown":
            send({"jsonrpc": "2.0", "id": message["id"], "result": None})
        elif method == "exit":
            break
        elif "id" in message:
            send({"jsonrpc": "2.0", "id": message["id"], "result": None})


if __name__ == "__main__":
    main()
