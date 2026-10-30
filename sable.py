#!/usr/bin/env python3
"""Sable: a small scripting language implemented as a tree-walking interpreter."""

import sys
import math
import bisect
from dataclasses import dataclass
from typing import Any, List, Optional

VERSION = "0.1.0"

sys.setrecursionlimit(10000)


class SableError(Exception):
    kind = "Error"

    def __init__(self, message, line=1, col=1):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col


class SableSyntaxError(SableError):
    kind = "SyntaxError"


class SableRuntimeError(SableError):
    kind = "RuntimeError"


KEYWORDS = {
    "let", "fn", "if", "else", "while", "for", "in", "return",
    "break", "continue", "true", "false", "nil", "and", "or", "not",
}


@dataclass
class Token:
    type: str
    value: Any
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, {self.line}:{self.col})"


class Lexer:
    def __init__(self, source):
        self.src = source
        self.pos = 0
        self.tokens = []
        self.line_starts = [0]
        for i, ch in enumerate(source):
            if ch == "\n":
                self.line_starts.append(i + 1)

    def position(self, offset):
        line = bisect.bisect_right(self.line_starts, offset)
        col = offset - self.line_starts[line - 1] + 1
        return line, col

    def error(self, offset, message):
        line, col = self.position(offset)
        raise SableSyntaxError(message, line, col)

    def add(self, type, value, start):
        line, col = self.position(start)
        self.tokens.append(Token(type, value, line, col))

    def scan(self):
        while self.pos < len(self.src):
            c = self.src[self.pos]
            if c in " \t\r\n":
                self.pos += 1
                continue
            if c == "/" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "/":
                self.pos += 2
                while self.pos < len(self.src) and self.src[self.pos] != "\n":
                    self.pos += 1
                continue
            if c == "/" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "*":
                start = self.pos
                self.pos += 2
                closed = False
                while self.pos + 1 < len(self.src):
                    if self.src[self.pos] == "*" and self.src[self.pos + 1] == "/":
                        self.pos += 2
                        closed = True
                        break
                    self.pos += 1
                if not closed:
                    self.error(start, "unterminated block comment")
                continue
            if c.isdigit():
                self.number()
                continue
            if c == '"':
                self.string()
                continue
            if c.isalpha() or c == "_":
                self.identifier()
                continue
            self.operator()
        line, col = self.position(len(self.src))
        self.tokens.append(Token("EOF", None, line, col))
        return self.tokens

    def number(self):
        start = self.pos
        while self.pos < len(self.src) and self.src[self.pos].isdigit():
            self.pos += 1
        if (self.pos + 1 < len(self.src) and self.src[self.pos] == "."
                and self.src[self.pos + 1].isdigit()):
            self.pos += 1
            while self.pos < len(self.src) and self.src[self.pos].isdigit():
                self.pos += 1
        if self.pos < len(self.src) and self.src[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.src) and self.src[self.pos] in "+-":
                self.pos += 1
            if self.pos < len(self.src) and self.src[self.pos].isdigit():
                while self.pos < len(self.src) and self.src[self.pos].isdigit():
                    self.pos += 1
            else:
                self.error(start, "malformed number")
        text = self.src[start:self.pos]
        try:
            value = float(text)
        except ValueError:
            self.error(start, f"malformed number {text!r}")
        self.add("NUMBER", value, start)

    def string(self):
        start = self.pos
        self.pos += 1
        out = []
        escapes = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}
        while self.pos < len(self.src):
            c = self.src[self.pos]
            if c == '"':
                self.pos += 1
                self.add("STRING", "".join(out), start)
                return
            if c == "\\":
                self.pos += 1
                if self.pos >= len(self.src):
                    self.error(start, "unterminated string")
                esc = self.src[self.pos]
                if esc not in escapes:
                    self.error(self.pos, f"unknown escape sequence \\{esc}")
                out.append(escapes[esc])
                self.pos += 1
                continue
            out.append(c)
            self.pos += 1
        self.error(start, "unterminated string")

    def identifier(self):
        start = self.pos
        while (self.pos < len(self.src)
               and (self.src[self.pos].isalnum() or self.src[self.pos] == "_")):
            self.pos += 1
        text = self.src[start:self.pos]
        if text in KEYWORDS:
            self.add(text, text, start)
        else:
            self.add("IDENT", text, start)

    def operator(self):
        start = self.pos
        two = self.src[self.pos:self.pos + 2]
        if two in ("==", "!=", "<=", ">=", "+=", "-=", "*=", "/="):
            self.pos += 2
            self.add(two, two, start)
            return
        c = self.src[self.pos]
        if c in "+-*/%=<>(){}[],:;":
            self.pos += 1
            self.add(c, c, start)
            return
        self.error(start, f"unexpected character {c!r}")


@dataclass
class Program:
    statements: List[Any]


@dataclass
class Let:
    line: int
    name: str
    value: Any


@dataclass
class FnDecl:
    line: int
    name: str
    params: List[str]
    body: Any


@dataclass
class If:
    line: int
    cond: Any
    then_branch: Any
    else_branch: Any


@dataclass
class While:
    line: int
    cond: Any
    body: Any


@dataclass
class For:
    line: int
    var: str
    iterable: Any
    body: Any


@dataclass
class Return:
    line: int
    value: Any


@dataclass
class Break:
    line: int


@dataclass
class Continue:
    line: int


@dataclass
class Block:
    line: int
    statements: List[Any]


@dataclass
class ExprStmt:
    line: int
    expr: Any


@dataclass
class Assign:
    line: int
    target: Any
    op: str
    value: Any


@dataclass
class Logical:
    line: int
    op: str
    left: Any
    right: Any


@dataclass
class Binary:
    line: int
    op: str
    left: Any
    right: Any


@dataclass
class Unary:
    line: int
    op: str
    operand: Any


@dataclass
class Call:
    line: int
    callee: Any
    args: List[Any]


@dataclass
class Index:
    line: int
    obj: Any
    index: Any


@dataclass
class Var:
    line: int
    name: str


@dataclass
class Literal:
    line: int
    value: Any


@dataclass
class ListLit:
    line: int
    elements: List[Any]


@dataclass
class MapLit:
    line: int
    pairs: List[Any]


@dataclass
class FnExpr:
    line: int
    params: List[str]
    body: Any


